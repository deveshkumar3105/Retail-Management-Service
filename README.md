# Retail Data Platform — Phase 1

A local synthetic Order Service built with FastAPI and SQLite. This phase intentionally implements one working source system; the future AWS lakehouse is not included.

## macOS setup and run

```bash
./scripts/setup_mac.sh
source .venv/bin/activate
pytest services/order_service/tests -q
python services/order_service/scripts/seed_orders.py --count 500 --seed 42
uvicorn services.order_service.app.main:app --reload
```

The UI is at `http://127.0.0.1:8000/`; it shows order summaries, search and status filters, item details, and an export link. The API docs are at `http://127.0.0.1:8000/docs`; health check: `http://127.0.0.1:8000/health`; Swagger UI: `http://127.0.0.1:8000/docs`.

The database defaults to `data/orders.db` and is created on startup. Set `ORDER_DATABASE_PATH` and `ORDER_LOG_LEVEL` to configure it; see `.env.example` (the app reads environment variables directly and does not load `.env`). Generated databases and virtual environments are ignored by Git.

## Example

```bash
curl -X POST http://127.0.0.1:8000/orders -H 'Content-Type: application/json' -d '{"customer_id":"customer-00001","currency":"USD","items":[{"product_id":"product-0001","quantity":2,"unit_price":"19.99","discount_amount":"2.00"}]}'
```

Response includes a generated stable `order_id`, `order_total: 37.98`, item rows, UTC timestamps, and `source_version: 1`. Money is accepted and returned as decimal strings and stored as integer cents.

## API

- `GET /health`
- `POST /orders`
- `GET /orders?limit=100&offset=0`
- `GET /orders/{order_id}`
- `PATCH /orders/{order_id}` (status transitions only)
- `GET /orders/changes?since=2025-01-01T00:00:00Z&limit=500&offset=0`
- `GET /exports/orders?since=...` (NDJSON; omit `since` for full export)

Allowed transitions: CREATED → CONFIRMED or CANCELLED; CONFIRMED → SHIPPED or CANCELLED; SHIPPED → DELIVERED. DELIVERED and CANCELLED are terminal. Reapplying the current state is idempotent. Duplicate explicit order IDs return 409.

## Incremental ingestion contract

See [docs/source-data-contracts.md](docs/source-data-contracts.md) for the JSONL contract, money and timestamp representation, pagination, and checkpoint limitations. Timestamp polling is a practical incremental extract, not complete CDC. The future extraction consumer should overlap checkpoints and deduplicate by `order_id`/`source_version` until a durable change log or transactional outbox is added.

## Continue the ecosystem

See [docs/architecture.md](docs/architecture.md) and [docs/next-steps.md](docs/next-steps.md) for service boundaries and implementation-ready plans for Customer, Product, Payment, and Returns services.
