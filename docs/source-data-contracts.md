# Source data contracts

Each service exports UTF-8 NDJSON (one JSON object per line), uses stable string identifiers, and emits UTC ISO-8601 timestamps with microsecond precision and a `Z` suffix. Monetary amounts in Order Service are decimal strings in the API/export and integer cents in SQLite.

## Order Service (v1)

`GET /exports/orders` emits complete orders with `order_id`, `customer_id`, `order_status`, `order_timestamp`, `currency`, `order_total`, `created_at`, `updated_at`, `source_version`, and an `items` array. Items contain `order_item_id`, `product_id`, `quantity`, `unit_price`, `discount_amount`, and `line_total`. Items sort by ID; full exports sort by `(order_timestamp, order_id)`, changes by `(updated_at, order_id)`. `/orders/changes?since=` uses a strict timestamp boundary. See `GET /docs` on the Order Service for schemas.

## Customer Service (v1)

Database: `data/customers.db`, separate from `data/orders.db`.

Current-state fields: `customer_id` (stable primary key), `first_name`, `last_name`, `email` (unique, case-insensitive), optional `phone`, `city`, `state`, `postal_code`, `country` (two-letter uppercase code), `customer_status` (`ACTIVE`/`INACTIVE`), `created_at`, `updated_at`, `source_version`, and `change_seq`. Names and addresses are synthetic. Email must use the reserved `.invalid` domain; optional phone must be in the fictional `+1-555-01xx` range. Deactivation is represented as an update to `customer_status=INACTIVE`, not deletion. Email changes update the current row and produce a new change event. A duplicate email or explicit ID returns HTTP 409.

`GET /exports/customers` emits the latest current customer row per ID in deterministic `customer_id` order. Each line contains all current-state fields above. `?since=<ISO-8601 timestamp>` emits change snapshots with `changed_at > since`. Prefer `?after_seq=<integer>` for incremental ingestion: it emits append-only snapshots with `change_seq > after_seq`, ordered by the database-generated monotonic sequence. The same cursor is available through `GET /customers/changes?after_seq=...`; its response includes `next_after_seq`. Add optional `customer_id=...` to inspect only one profile’s history. Commit the returned sequence only after its page is durably landed. `since` and `after_seq` are mutually exclusive. The changes endpoint supports bounded `limit` and `offset`; for sequence polling, advance from `next_after_seq` and leave offset at zero to avoid skipping events.

The `customer_changes` table is written in the same SQLite transaction as each create/update and records an immutable JSON snapshot, operation, timestamp, version, and sequence. This is a lightweight transactional change log (CDC-like source contract), stronger than polling the mutable customer table, but it is not a database-log CDC connector. There is currently no delete operation; inactive status is the business deletion/deactivation signal. If hard deletes are introduced, emit a tombstone event rather than removing the history. Timestamp polling still has strict-boundary and precision concerns; sequence polling avoids timestamp tie/checkpoint ambiguity. Offset pagination against the append-only log is stable, but sequence cursor pagination is the recommended approach.

### Sample export row

```json
{"customer_id":"customer-00001","first_name":"Reese","last_name":"Reed","email":"customer-00001@example.invalid","phone":"+1-555-0101","city":"Albany","state":"New York","postal_code":"68555","country":"US","customer_status":"ACTIVE","created_at":"2024-02-29T00:29:00.000000Z","updated_at":"2024-02-29T00:29:00.000000Z","source_version":1,"change_seq":1}
```

### Raw ingestion and quality checks

A future scheduled extractor can land each full snapshot under a service/source/date/run partition such as `s3://<bucket>/raw/customer_service/extract_date=YYYY-MM-DD/run_id=<id>/customers.jsonl`, while sequence-based incremental files can be named with their sequence range. Preserve source JSON and extraction metadata in raw storage; validate and quarantine downstream before curated Iceberg writes. Useful quality checks: non-null stable ID, unique ID, case-insensitive unique email, email domain `.invalid` in synthetic environments, valid status, two-letter country, non-null creation/update timestamps, `source_version >= 1`, and strictly increasing sequence per event. Track schema version in extraction metadata; additive nullable fields can be introduced with a documented contract version, while renames/type changes require a new version or explicit compatibility mapping.
