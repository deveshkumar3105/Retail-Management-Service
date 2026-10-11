# Next source services — implementation plan

## Current state

Order Service and Customer Service are implemented as isolated FastAPI + SQLite applications. Customer seed IDs intentionally match the Order Service's `customer-00001`–`customer-02000` reference format. Customer has a transactional append-only sequence log. Read `docs/source-data-contracts.md` before extending either service.

Continue one service at a time using `services/<name>_service/app`, tests, and seed scripts; give each service a dedicated `data/<name>.db`. Keep startup independent, use stable string IDs, synthetic fixtures, UTC timestamps, explicit transactions, request validation, health/list/detail/create/update endpoints, deterministic pagination, tests, and a documented full and incremental export. Do not add cross-service network calls or combine the databases.

## Product Service

Database `data/products.db`. Tables: `categories(category_id PK, name, parent_category_id nullable)` and `products(product_id PK, sku UNIQUE, name, category_id FK, current_price_cents, currency, is_active, created_at, updated_at, source_version)`, plus append-only product changes with monotonic sequence and old/new snapshots. Endpoints: `GET /health`, category read/create, `POST /products`, paginated `GET /products`, `GET /products/{product_id}`, `PATCH /products/{product_id}`, `GET /products/changes?after_seq=...`, `GET /exports/products?after_seq=...`. Acceptance: category FK and currency/price validation; price changes versioned; seeded product IDs use `product-0001` through `product-0500` to match current order fixture references; deterministic/idempotent seed; tests cover constraints, changes, export, and isolation.

## Payment Service

Database `data/payments.db`. Tables: `payments(payment_id PK, order_id external reference, payment_status, amount_cents, currency, payment_method_token, created_at, updated_at, source_version)` and append-only `payment_events(event_id PK, payment_id FK, event_type, occurred_at, amount_cents, reason_code nullable, sequence)`. Never store card numbers, security codes, bank credentials, or real payment details; use test tokens such as `tok_test_...`. Model attempts, success, failure, and refunds as events; refunds reference the original payment and cannot exceed the captured amount. Endpoints: `POST /payments`, `POST /payments/{payment_id}/events`, list/detail, changes by sequence, JSONL export. Acceptance: idempotency key, legal transitions, immutable event history, reconciliation, synthetic fixtures, tests for retry/failure/success/refund/idempotency/export. `order_id` is external; startup must not query Order Service.

## Returns Service

Database `data/returns.db`. Tables: `returns(return_id PK, order_id external reference, return_status, reason_code, requested_at, updated_at, source_version)`; `return_items(return_item_id PK, return_id FK, order_item_id external reference, product_id, quantity, resolution, refund_amount_cents nullable)`; append-only `return_events(event_id PK, return_id FK, status, occurred_at, sequence)`. Statuses: REQUESTED, APPROVED, REJECTED, RECEIVED, REFUNDED, CLOSED with explicit transitions. Endpoints: create, paginated list/detail, status update, sequence-based changes, full/incremental JSONL export. Acceptance: positive quantities and resolution validation; no cross-database FK; seeded order/item references; known-value refund ceiling; immutable status events; tests for transitions and export.

## Pipeline readiness acceptance

Each source is complete when it starts independently, has reproducible synthetic fixtures, passing local tests, a stable full export and reliable sequence-based incremental extract, clear data quality rules, and a contract documenting schema evolution. Preserve source files unchanged in a future S3 raw zone; then implement Glue/PySpark validation and quarantine, curated Iceberg tables/catalog, and orchestration. Do not claim timestamp polling alone is complete CDC.
