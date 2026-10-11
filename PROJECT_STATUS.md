# Retail Lakehouse Platform — project status

**Project name:** Retail Lakehouse Platform — Local Retail Source Systems

## Completed

- Order Service: FastAPI API and small browser UI, isolated `data/orders.db`, synthetic order seeder, pagination, status transitions, timestamp-based changes, NDJSON export, and tests.
- Customer Service: independently runnable FastAPI API with a lightweight browser UI, isolated `data/customers.db`, validated synthetic profile creation/updates, status deactivation, transactionally recorded customer change snapshots with monotonic `change_seq`, deterministic pagination, changes and NDJSON exports, and seeded customer profiles.
- Documentation: local architecture, source contracts, continuation plan, and macOS setup/run instructions.

## Commands

From the repository root on macOS:

```bash
./scripts/setup_mac.sh
source .venv/bin/activate
pytest services/order_service/tests services/customer_service/tests -q
python services/customer_service/scripts/seed_customers.py --count 2000 --seed 42
uvicorn services/customer_service.app.main:app --reload --port 8001
```

Customer UI: `http://127.0.0.1:8001/`; Customer API: `http://127.0.0.1:8001`; Swagger UI: `http://127.0.0.1:8001/docs`; health: `http://127.0.0.1:8001/health`. For the existing Order Service, run separately on port 8000 with `uvicorn services.order_service.app.main:app --reload --port 8000`.

To add customer IDs 2001–2500 later: `python services/customer_service/scripts/seed_customers.py --count 500 --start 2001 --seed 42`. Seeders skip already present IDs. Export current data at `/exports/customers`, or incremental events at `/exports/customers?after_seq=0`. Customer change API pages expose `next_after_seq`; save it only after the page lands safely.

## Verification tracking

- Customer Service tests: **9 passed** (`pytest services/customer_service/tests -q`).
- Order Service tests: **8 passed** (`pytest services/order_service/tests -q`).
- `compileall` for both services and `node --check` for the Order UI JavaScript passed.
- Customer seed CLI created 2,000 rows, safely reran with zero duplicates, then added customer 2,001. The database had 2,001 customer rows and 2,001 change events; full and incremental exports returned 2,001 rows from the expected ranges. The existing 500-row Order database remained unchanged.
- Uvicorn binding was not separately exercised in this restricted run; FastAPI startup and routes were exercised through `TestClient`.

A test pass validates local behavior; it does not establish cloud ingestion or production infrastructure.

## Remaining work

- Build Product, Payment, and Returns services using the concrete schemas and acceptance criteria in `docs/next-steps.md`.
- Later: add service-level source schema versions, cursor/snapshot behavior for larger extracts, and S3/Glue/Iceberg ingestion only after local source contracts are established.
