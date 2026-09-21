# Built-system smoke

`make smoke` runs pytest against a real built, non-root Gunicorn application.
It does not use Flask's test client or call application internals.

`scripts/smoke/runtime.py` owns a unique disposable DEV Compose project, generated
password and available loopback port. It builds images, migrates its database,
starts the application, requires exact HTTP 200 `Healthy`, and launches the tooling
container on the same private network. Pytest exit status propagates to Make.
The runner and stack are removed in `finally`, including failed assertions.
No Docker socket or developer source is mounted into the smoke runner.

`tests/smoke/` owns liveness, readiness, local Swagger/OpenAPI, Item CRUD,
Action CRUD/nesting/cascade, persistence, cache fill/hit/TTL/invalidation, stale-child
protection, and representative Problem Details checks. These are representative
built-system checks; exhaustive validation remains integration-owned.

`tests/fixtures/smoke.py` supplies a small HTTP client and observers. PostgreSQL
observations are read-only; Redis observations use only the owned stack. All domain
mutations go through HTTP. Each test creates its own parent Item and cleans it up
through HTTP; stack disposal is the final cleanup boundary even if the app fails.
Provider URLs are generated for private `postgres`/`redis` service names and must
match the owned DEV profile. No developer LOCAL/DEV configuration is loaded.

The runtime contains lifecycle orchestration, not duplicate domain assertions.
The shared standard-library HTTP helper in `scripts/http_client.py` is also used
by workflow readiness/persistence probes. Collection requires `--smoke`; ordinary
application tests never run this suite accidentally.
