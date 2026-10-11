# Retail Lakehouse Platform — local source architecture

The project is named **Retail Lakehouse Platform — Local Retail Source Systems**. It is a portfolio source-system project intended to feed a future lakehouse; AWS infrastructure is not implemented in this phase.

Each bounded context is an independently runnable Python/FastAPI application with its own SQLite file and domain logic. Services start without contacting one another.

```text
Order API    → data/orders.db
Customer API → data/customers.db
Product API  → data/products.db (planned)
Payment API  → data/payments.db (planned)
Returns API  → data/returns.db (planned)
```

Order Service runs on port 8000 and Customer Service on port 8001 when started together. Current synthetic Order records refer to customer IDs formatted `customer-00001` through `customer-02000`, randomly selected from that range. Customer Service seed IDs deliberately use the same format and deterministic numeric range, so the records can join on `customer_id` without a service call or shared database. A 500-customer seed only covers IDs 1–500; seed 2,000 customers for complete coverage of all current order references. Independently created API IDs are UUIDs and should not be expected to match an order's customer ID unless the caller supplies the intended ID. The services do not enforce cross-database foreign keys.

The eventual ingestion path is REST or scheduled source export → S3 raw → Glue PySpark validation/quarantine → Iceberg curated tables → Glue Catalog/Athena. Airflow orchestration can be added later. No cloud credentials or external services are needed for local development.

Both services use FastAPI schemas at the boundary, explicit SQLite transactions, UTC ISO-8601 timestamps, and source versions. Order money is stored as integer cents. Customer changes additionally use a transactionally written append-only change log with a monotonic sequence. See `source-data-contracts.md` for ingestion contracts and limits.
