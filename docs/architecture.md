# Local source-system architecture

Each bounded context will be an independently runnable Python/FastAPI application with its own SQLite file and domain logic. Services start without contacting one another. IDs are stable synthetic references; this phase does not enforce cross-service foreign keys because databases are intentionally isolated.

```text
Order API → data/orders.db
Customer API → data/customers.db
Product API → data/products.db
Payment API → data/payments.db
Returns API → data/returns.db
```

The eventual ingestion path is REST or scheduled source export → S3 raw → Glue PySpark validation/quarantine → Iceberg curated tables → Glue Catalog/Athena. Airflow can orchestrate it later. This repository currently implements only Order Service, with no cloud credentials or cloud dependencies.

Each service uses FastAPI schemas at the boundary, explicit SQLite transactions, integer cents, UTC ISO-8601 timestamps, and versioned records. Keep schema/domain code and the database file within the service boundary. For cross-service relationships, validate with deterministic IDs in generated fixtures; do not make service startup depend on synchronous calls to sibling services.
