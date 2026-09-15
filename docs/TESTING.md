# Testing the Flask reference

UNIT TESTS FOLLOW LOGIC

INTEGRATION TESTS FOLLOW BOUNDARIES

SMOKE TESTS FOLLOW BUILT SYSTEM

ROUTES: INTEGRATION

## Coverage ownership

| Concern | Evidence |
| --- | --- |
| Settings, schemas, enums | Provider-free unit validation and explicit environment isolation |
| Services | Controlled transaction/repository/cache collaborators; missing resources, cache decisions, flush/commit failure ordering |
| Cache wrappers | Keys, TTL arguments, typed scalar roundtrips, malformed/wrong-ID payload rejection |
| Routes | Real Flask binding, exact methods/paths, JSON fields, statuses, Location, errors, immutable parent |
| PostgreSQL | Real migration, repositories, constraints, rollback, cascade, ordering, row-lock update/delete race |
| Redis | Real serialization, expiration, invalidation, stale-child protection, ACL outage/recovery, connection failure |
| Readiness | Healthy, Degraded, Unhealthy, bad revision, missing table/column, database authentication failure |
| OpenAPI | Exact resource surface, schemas, enums, name limits, error media type, Location |
| Foundation | Import safety, multiple app instances, session teardown, Problem Details retained |

No route unit suite and no historical .NET test-count target. No external football
API or credentials are needed. Use the Make targets below; direct pytest still supports explicit TEST provider
variables. Python dependencies live only in requirements.txt.

## Isolation and lifecycle

Supply only intentionally disposable PostgreSQL/Redis instances. PostgreSQL tests
require TEST_DATABASE_URL, a `goalstats_test_*` database, and
TEST_DATABASE_DISPOSABLE=1. Redis requires TEST_REDIS_URL and
TEST_REDIS_DISPOSABLE=1. Missing provider URLs cause explicit skips; supplied invalid
or unavailable providers fail. Fixtures never fall back to developer DATABASE_URL
or REDIS_URL. Do not point these variables at valuable databases or shared caches.

The PostgreSQL fixture applies Alembic migrations, removes reference-domain rows
before/after each provider test, and drops its uniquely named probe tables. Migration
tests perform destructive downgrade/re-upgrade only in this disposable database.
Redis tests use unique per-test prefixes, delete only their own keys, and remove
only their own temporary ACL user. App fixtures close Redis pools and dispose Engines.
Use one dedicated provider pair per concurrent pytest process; xdist/shared-provider
parallelism is not configured.

Tests use real PostgreSQL transactions for persistence and commit/rollback evidence.
A focused injected before-commit failure proves the actual flushed database change
rolls back without invalidating a cached value. Redis permission failures are induced
on a dedicated ACL user, then reversed to verify recovery. No global FLUSHALL or
shared user/ACL mutation is used.

## Migration verification

The initial revision is b7f42e9c1a60. Verify an empty database upgrades, repeated
upgrade is safe, downgrade/re-upgrade works, and `alembic check` finds no model drift.
Future model changes require reviewed revisions and updated readiness expectations.
Foundation assertions about empty metadata/empty OpenAPI were intentionally evolved
with the reference domain; the original lifecycle and error behaviors remain covered.

## Commands and evidence

- `make unit`: provider-free tests in a network-disabled tooling container.
- `make integration`: isolated real PostgreSQL/Redis; migrations before integration pytest.
- `make test`: one pytest run covering unit and integration, not duplicated target chaining.
- `make coverage`: the full suite with terminal line coverage; no arbitrary threshold.
- `make check`: Ruff lint, formatting check, strict source/migration mypy.
- `make smoke`: disposable built DEV, real HTTP, PostgreSQL and Redis.
- `make certify`: independent disposable LOCAL/DEV plus failure/cleanup scenarios.

Smoke checks liveness/readiness, locally served Swagger/spec, CRUD/Location, nested
Actions, direct database persistence, Redis fill/hit/TTL/invalidation, stale children
after cascade, and safe Problem Details. The cache-hit observation uses Redis hit
counters without poisoning cache or modifying database records behind the app.

Workflow certification verifies repeated migrations, downgrade/re-upgrade, drift
checks, non-root runtime, DEV without mounts/debug, clean Gunicorn termination,
LOCAL/DEV data persistence across stop/start, TEST row/key isolation, and provider
outages. Degraded is explicitly rejected by startup waits. It induces unit-runner,
integration-runner, migration, provider-startup, and smoke failures, then asserts
owned disposable containers/networks/volumes are gone. Both SIGTERM and SIGINT are
sent while a real TEST runner is active. Existing resources and an unrelated sentinel
must survive; all certification-owned disposable resources are removed.

Unit/integration failure injection uses a deliberately missing required pytest plugin
so the real pytest process fails before execution. The normal full suite separately
proves test assertions pass. Migration/provider/smoke failures exercise their actual
workflow stages. No failure is reclassified as a passing test suite.

Coverage files and quality caches remain inside disposable containers. Scripts are
Ruff-checked; mypy remains strict over application and migrations. Host orchestration
uses the Python standard library. Documentation of a check is not a substitute for
executing it; final publication requires Prompt 4's independent certification.
