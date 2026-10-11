# Next source services — implementation plan

Implement one service at a time using the Order Service conventions: a dedicated `services/<name>_service/app`, tests, seed script, and independent database under `data/`; FastAPI/OpenAPI; SQLite; integer minor-unit money; UTC timestamps; `created_at`, `updated_at`, and monotonic per-record `source_version`; explicit transactions; synthetic deterministic fixtures; `/health`, paginated list, detail, changes, and complete JSONL export. Keep startup independent and avoid cross-service network calls. Use deterministic IDs so separately seeded datasets relate without sharing a database.

## Customer Service

Database `data/customers.db`. `customers(customer_id PK, email_synthetic UNIQUE, first_name, last_name, phone_synthetic nullable, created_at, updated_at, source_version, is_active)` and append-only `customer_profile_changes(change_id PK, customer_id, changed_at, changed_fields_json, source_version)`. Seed synthetic profiles only; use reserved `.invalid` emails and fictional phone values, never real contact data. Endpoints: `POST /customers`, `GET /customers`, `GET /customers/{customer_id}`, `PATCH /customers/{customer_id}` for profile updates, `GET /customers/changes?since=`, `GET /exports/customers?since=`. Acceptance: duplicate IDs/email produce 409; changes increment versions and retain change records; seed is reproducible/idempotent; pagination and export include update metadata; tests cover validation and update behavior.

## Product Service

Database `data/products.db`. Tables `categories(category_id PK, name, parent_category_id nullable)` and `products(product_id PK, sku UNIQUE, name, category_id FK, current_price_cents, currency, is_active, created_at, updated_at, source_version)`; append-only `product_changes(change_id PK, product_id, changed_at, old_values_json, new_values_json, source_version)`. Endpoints: category CRUD/read as appropriate, `POST /products`, `GET /products`, `GET /products/{product_id}`, `PATCH /products/{product_id}`, `GET /products/changes?since=`, `GET /exports/products?since=`. Acceptance: positive/zero policy is explicit, currency validated, category FK enforced, price changes are versioned, deterministic synthetic catalog and tests cover FK/price changes/export.

## Payment Service

Database `data/payments.db`. `payments(payment_id PK, order_id, payment_status, amount_cents, currency, payment_method_token, created_at, updated_at, source_version)` plus `payment_events(event_id PK, payment_id, event_type, occurred_at, amount_cents, reason_code nullable)`. `order_id` is a stable external reference, intentionally not a SQLite FK. Never store card numbers, security codes, bank credentials, or real payment details; use tokens like `tok_test_...`. Model attempts, success, failure, and refunds as append-only events; a refund is a separate negative/refund event linked to original payment. Endpoints: `POST /payments` (attempt), `POST /payments/{id}/events`, list/detail, changes, and export. Acceptance: idempotency key for attempt/event submission; allowed state transitions and partial-refund ceiling; event history immutable; amounts reconcile; synthetic data only; tests cover retry, failure, success, refunds, idempotency, and export.

## Returns Service

Database `data/returns.db`. `returns(return_id PK, order_id, return_status, reason_code, requested_at, updated_at, source_version)` and `return_items(return_item_id PK, return_id FK, order_item_id, product_id, quantity, resolution, refund_amount_cents nullable)` plus append-only `return_events(event_id PK, return_id FK, status, occurred_at)`. Order and order item IDs are stable external references, not cross-database FKs. Endpoints: `POST /returns`, list/detail, `PATCH /returns/{id}/status`, changes, export. Support requested, approved, rejected, received, refunded, and closed transitions with explicit rules. Acceptance: positive quantities and resolutions validated; item references can be checked against an imported order fixture but service starts offline; refunds cannot exceed item/order value when known; events are append-only; tests cover transition rules and stable JSONL export.

## Cross-service fixture and interview milestones

1. Seed Order first to produce customer/product references; Customer and Product seeders must be able to emit the same deterministic ID ranges or accept an ID manifest.
2. Add Payments referencing seeded order IDs and Returns referencing order/order-item IDs without service-to-service startup dependencies.
3. Add change-log/outbox sequences to each service before claiming robust CDC. Add pagination cursor/snapshot behavior before large exports.
4. Only after each local service has passing tests and an ingestion contract, design AWS ingestion (S3 raw layout, Glue/PySpark validation and quarantine, Iceberg curated schema, catalog, and orchestration).

Each service is complete when setup, seed, API, tests, incremental changes, full/incremental JSONL export, and documentation work independently without Docker or cloud credentials.
