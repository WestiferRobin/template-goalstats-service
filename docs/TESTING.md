# Testing

[README](../README.md) · [Architecture](ARCHITECTURE.md) · [Development and environment setup](DEVELOPMENT.md)

For contributors choosing, writing or running tests, this guide explains what each
level proves and how to select existing helpers safely. Newcomers can start with
[commands](#commands) and the [first contribution exercise](DEVELOPMENT.md#first-exercise-two-host-configuration-isolation).
Reviewers can jump to [test placement](#test-placement), [helpers](#test-helpers)
and [infrastructure safety](#infrastructure-safety).

## Mental model

UNIT TESTS FOLLOW LOGIC

INTEGRATION TESTS FOLLOW BOUNDARIES

SMOKE TESTS FOLLOW BUILT SYSTEM

| Level | Meaning |
| --- | --- |
| UNIT | Isolated application-owned logic/contracts with deterministic collaborators; no hosted ASP.NET application, real PostgreSQL/Redis or external network |
| INTEGRATION | Actual framework/provider collaboration: hosting, DI, routing, binding, configured serialization, exception handling, EF/PostgreSQL or Redis |
| SMOKE | Built service/image, real startup and HTTP, health/readiness, representative behavior and dependency wiring |
| WORKFLOW CERTIFICATION | Lifecycle, persistence, cleanup and controlled failure/interruption |
| NO DIRECT TEST | Passive plumbing or generated artifacts whose consumers/schema tests prove the behavior |

Ordinary in-process DataAnnotations and JSON contract tests can be unit tests.
The SDK container used by `make unit` is a launcher, not a provider dependency.
Integration does not mean every test needs a database or Docker.

The primary goal is **risk-based architectural behavior coverage**. Branch coverage
is a secondary diagnostic; line coverage is a tertiary diagnostic. Neither a fixed
test count nor 100% coverage is the goal. Protect data integrity, cancellation,
service failures, cache consistency, provider outages, public contracts and cleanup.

### Where does this test go?

1. Does it start the built service and call the external interface? **SMOKE / WORKFLOW.**
2. Does it require real ASP.NET hosting, DI, routing, binding, EF, PostgreSQL, Redis or another provider boundary? **INTEGRATION.**
3. Can it prove an application-owned decision/contract with isolated inputs/doubles? **UNIT.**
4. Does another test prove the same requirement through the same mechanism? **CONSOLIDATE.**
5. Is it passive plumbing with no independent behavior? **NO DIRECT TEST.**

## Source-first test design

**Production behavior → required cases → correct test level → implementation.**
Read the affected source and current tests before choosing a helper or adding cases.
For behavior that exists, consider success, failure, boundary, special cases, state
transitions, validation, serialization, cancellation, timeout, logging,
configuration and infrastructure. Do not manufacture a case in every category for
a passive type or duplicate the same evidence across levels.

For example, a service write can require evidence that persistence completes
before invalidation starts, that a persistence failure prevents invalidation, and
that committed-write invalidation uses its intended cancellation policy. Merely
recording that both methods were called does not establish completion ordering.
A HTTP-only formatting change needs public JSON evidence; it does not inherently
need a new PostgreSQL test or migration.

## Test placement

Production paths are relative to `src/GoalStats.Template.Api/`. Test projects are
[GoalStats.Template.Api.UnitTests](../tests/GoalStats.Template.Api.UnitTests) and
[GoalStats.Template.Api.IntegrationTests](../tests/GoalStats.Template.Api.IntegrationTests); match the
existing feature folders rather than creating another test project.

| Subject | Established level | Evidence / placement |
| --- | --- | --- |
| DTO / Request | BOTH | Validation/serialization in unit `Dtos/`; HTTP binding indirectly in integration `Controllers/` |
| Enum | UNIT | Meaningful values/validation in unit `Enums/`; public representation indirectly in HTTP/OpenAPI tests where relevant |
| Model | BOTH | Meaningful defaults in unit `Models/`; persistence in integration `Infrastructure/Database/` |
| Mapper | UNIT | DTO → Response fields in unit `Mappers/` |
| Service | BOTH | Unit business decisions, validation, ordering/cancellation and cache policy; existing HTTP/infrastructure integration proves real persistence/cache collaboration |
| Controller | INTEGRATION | Production routes, binding, request abort, service failures, ownership, JSON/status/headers in integration `Controllers/` |
| Exception classes | UNIT | Safe messages, identifiers and meaningful defaults in unit `Exceptions/` |
| ApiExceptionHandler | INTEGRATION | Hosted ProblemDetails/error behavior and real registered writer/JSON boundary in integration `Exceptions/` |
| CacheOptions | BOTH | Validation in unit `Infrastructure/Cache/`; binding and startup validation in integration `Startup/` |
| RedisCache | BOTH | Timeout/cancellation/failure policy in unit `Infrastructure/Cache/`; real TTL, serialization and recovery in integration `Infrastructure/Cache/` |
| ItemCache / ActionCache | BOTH | Resource keys/TTL/delegation in unit `Infrastructure/Cache/`; real roundtrips/isolation and HTTP cache behavior in integration `Infrastructure/Cache/` and `Controllers/` |
| Repository | INTEGRATION | Real queries, writes, tracking, constraints and races in `Infrastructure/Database/Repositories/` |
| TemplateDbContext | INTEGRATION | Save/timestamp behavior and persistence in `Infrastructure/Database/` |
| EF Configuration | INTEGRATION | Actual schema constraints and persistence, not just reading configuration code |
| Migration | INTEGRATION | Clean application, current state, rollback/reapplication and model agreement in `Infrastructure/Database/MigrationTests.cs` |
| Health check | INTEGRATION | Real provider/schema states in `Health/`; operational HTTP transport in `Controllers/MetaControllerTests.cs` |
| Extensions | INTEGRATION | Registration, options and provider/host behavior in `Startup/` and relevant infrastructure tests |
| Program / configuration | INTEGRATION | Actual hosting, middleware, endpoints and configuration through `Startup/`, `Controllers/`, `Exceptions/`, `OpenApi/` and `Health/` |
| Properties/launchSettings.json | NO DIRECT TEST | Relevant launch/runtime behavior is checked indirectly by startup/workflows |
| Interfaces | NO DIRECT TEST | Test implementations and consumers |
| Generated migration designer / snapshot | NO DIRECT TEST | Verify through migration/model agreement and schema tests; review generated diffs |

### Architecture rules

**CONTROLLERS: INTEGRATION.** Controllers stay thin: HTTP input → service invocation
→ HTTP response. Business decisions belong in Services. There is no unit
`Controllers/` suite for call counts, argument-forwarding matrices or concrete
ActionResult types. Hosted tests prove the meaningful transport contract.

Exception classes → unit; exception-to-HTTP handling → integration. Models have
unit defaults/object behavior and database integration for persistence, relationships,
constraints, timestamps and cascades. Services have isolated business behavior and
real-provider collaboration evidence; existing HTTP/cache tests can supply that
integration evidence without creating another `Services/` directory.

**BOTH does not mean duplicate assertions.** For every test ask: **WHAT UNIQUE
FAILURE MECHANISM DOES THIS TEST PROVE?** A fake Redis failure proves fallback
policy; a real Redis outage proves provider failure integration. Mapping Name twice
with the same in-memory mapper proves nothing new. Do not mock the boundary that
an integration test claims to certify. Do not create mirrored integration Enums,
Mappers, Models or Dtos directories, direct Properties tests, or fake EF repository
unit tests merely for symmetry.

### Infrastructure by actual concern

| Production location | Policy | Unique responsibility |
| --- | --- | --- |
| Database/TemplateDbContext | INTEGRATION | Real EF state tracking, timestamp stamping and saves |
| Database/Configurations | INTEGRATION | Actual model/schema constraints, indexes and relationships |
| Database/Migrations | INTEGRATION | Application, rollback/reapplication and model agreement |
| Database/Repositories/Item | INTEGRATION | PostgreSQL query ordering, tracking, writes and cancellation |
| Database/Repositories/Action | INTEGRATION | Above plus FK behavior, ownership and races |
| Database/PostgresHealthCheck | INTEGRATION | Provider/schema readiness and cancellation |
| Cache/RedisCache | BOTH | Unit timeout/cancellation/fallback; real Redis payload, expiry and recovery |
| Cache/CacheOptions | BOTH | Unit defaults/validation; actual binding/startup validation |
| Cache/Item and Cache/Action | BOTH | Unit keys/TTL; real roundtrip, invalidation and isolation |
| Cache/RedisHealthCheck | INTEGRATION | Real probe, degradation, cancellation and recovery |
| Interfaces | NONE directly | Implementations/consumers own evidence |
| Generated migration designer/snapshot | NONE directly | Migration/schema/model integration owns evidence |

No separate pure health component is manufactured for test symmetry.

### Directory ownership

Unit folders follow logic: `Dtos`, `Enums`, `Exceptions`, `Infrastructure/Cache`,
`Mappers`, `Models`, `Services`, `TestSupport`.
Integration folders follow boundaries: `Controllers`, `Exceptions`, `Health`,
`Infrastructure/Cache`, `Infrastructure/Database/Repositories`, `OpenApi`, `Startup`,
`FixtureTests`. `Fixtures` contains helpers, not test classes. `tests/Support`
contains linked pure test-support source shared by the two projects; UnitTests
never references IntegrationTests. Create folders only when actual tests need them.

## Naming and deterministic unit tests

Use `Method_WhenCondition_ExpectedResult`; for cross-method behavior use
`Behavior_WhenCondition_ExpectedResult`. Illustrative names, not a list of existing tests:

```text
GetAsync_WhenCacheMisses_LoadsRepository
CreateAsync_WhenParentIsMissing_ThrowsItemNotFound
CheckHealthAsync_WhenDatabaseIsUnavailable_ReturnsUnhealthy
WriteLifecycle_WhenPersistenceIsPending_DoesNotInvalidateCache
```

Unit tests must not require PostgreSQL, Redis, Docker, WebApplicationFactory or
network access. Use deterministic doubles and meaningful public outcomes. For
async orchestration, hold a dependency operation pending, await its started signal,
assert the service operation has not completed and later work has not started,
then release it and verify the result. Exercise failure/cancellation where the
source supports them. Bound waits so regressions fail instead of hanging; avoid
arbitrary sleeps or assertions based only on invocation order.

## Operational controller coverage

MetaController owns `/health` and `/ready` and delegates to the real ASP.NET health
middleware/service. Its integration tests characterize exact status/body bytes,
`text/plain`, anti-cache headers, Accept behavior, unrestricted methods (GET is the
documented interface), tag selection and request abort. Deterministic registered
IHealthCheck doubles isolate transport while preserving framework aggregation.
The HEAD body assertion characterizes TestServer. Built-server certification also
verified that Kestrel suppresses the HEAD wire body, matching the old endpoint mapping. Existing OpenAPI tests preserve exclusion of both routes.

Provider Health tests retain real PostgreSQL/Redis faults, budgets and recovery.
No unit controller suite or duplicated provider fault matrix is needed. Readiness
can be HTTP 200 `Degraded`; operational waits still require HTTP 200 plus `Healthy`.

## Integration rules

Integration tests may use WebApplicationFactory, real PostgreSQL/Redis, EF migrations,
actual configuration and HTTP requests. Do not mock the boundary being certified:
a mocked repository cannot prove a PostgreSQL constraint, and direct controller
calls cannot prove HTTP routing or JSON binding. Substitute unrelated dependencies
only when that keeps the intended boundary real and clear.

Not every integration test needs Docker. Hosted binding and configuration cases can
run without providers; tests marked `Category=Postgres` or `Category=Redis` require
the corresponding dedicated TEST connection. Missing infrastructure is a setup
failure, not a reason to silently skip provider evidence.

## Test helpers

Follow each linked helper and its callers before extending it. Keep test mechanisms
out of production registration and choose the smallest helper that proves the behavior.

| Helper / source | What it does | When to use it | When not to use it |
| --- | --- | --- | --- |
| [ApiFactory](../tests/GoalStats.Template.Api.IntegrationTests/Fixtures/ApiFactory.cs) | Ordinary WebApplicationFactory host in Testing; clears inherited configuration sources, loads base JSON, disables OpenAPI and supplies a unique cache prefix; explicit host overrides can follow | Hosted HTTP/DI tests with deliberate per-host dependency overrides | Unit tests or checking environment-specific JSON defaults; it does not provision PostgreSQL/Redis |
| [ConfigurationApiFactory](../tests/GoalStats.Template.Api.IntegrationTests/Fixtures/ConfigurationApiFactory.cs) | Loads base and selected environment JSON without shell/command-line/user-secret configuration, then explicit overrides; default environment is Production | Environment defaults, OpenAPI gates, options binding and invalid startup configuration | Ordinary CRUD setup, or claims that the factory proves ambient shell precedence |
| [PostgresFixture](../tests/GoalStats.Template.Api.IntegrationTests/Fixtures/PostgresFixture.cs) | Requires a connection targeting `goalstats_template_test`; creates/migrates a generated `goalstats_template_test_<guid>` database and a host, then disposes/deletes its owned database | Real PostgreSQL repository, persistence and HTTP cases | LOCAL/DEV connections, starting Docker, or assuming Redis is enabled: its host explicitly sets Redis empty unless a test overrides it |
| [PostgresOperations](../tests/GoalStats.Template.Api.IntegrationTests/Fixtures/PostgresOperations.cs) | Creates fixture-connected contexts and observes real PostgreSQL lock waits with bounded polling | Transaction, locking and cancellation tests requiring an observed database state | General HTTP setup or replacing real locking evidence with a guessed delay |
| [RedisProxy](../tests/GoalStats.Template.Api.IntegrationTests/Fixtures/RedisProxy.cs) | Owned TCP proxy to real Redis with response pause/disconnect and forwarding signals | Real transport failures, in-flight operations and recovery | A fake Redis server, unit tests, or faults against resources the test does not own |
| [RecordingLoggerProvider](../tests/GoalStats.Template.Api.IntegrationTests/Fixtures/RecordingLoggerProvider.cs) | Captures messages/structured entries for selected API/service/framework categories; accepts additional categories | Hosted logging assertions, event ownership and sensitive-data checks | Assuming all categories are recorded by default; add a new resource's category explicitly |
| [RecordingCache](../tests/GoalStats.Template.Api.UnitTests/Infrastructure/Cache/RecordingCache.cs) | ICache double recording operation, key, type, value, TTL and token; supplies result/failure | Domain-cache wrapper delegation/key/TTL unit tests | Real Redis serialization/expiry/provider behavior |
| [PendingCall](../tests/GoalStats.Template.Api.UnitTests/Services/PendingCall.cs) | Controlled async operation with started signal and explicit completion/failure; supports cancellation and releases pending work on disposal | Service completion ordering and failure/cancellation unit tests | Real database locks or provider timing certification |
| [FakeDistributedCache](../tests/GoalStats.Template.Api.UnitTests/Infrastructure/Cache/FakeDistributedCache.cs) | Controlled distributed-cache payload, failure, pending operation, signals and recorded calls/options | RedisCache adapter policy without network access | Proving that Redis itself serializes, expires or recovers correctly |

The shared [FixtureCleanup](../tests/Support/FixtureCleanup.cs) helper preserves both
host-disposal and database-cleanup failures without skipping cleanup. Its pure
orchestration is tested under unit `TestSupport`; owned database creation/disposal
failures remain under integration `FixtureTests/PostgresFixtureTests`. Redis proxy
observation belongs in `FixtureTests/RedisProxyTests`; production provider readiness stays
in `Health`; operational HTTP transport belongs to `Controllers/MetaControllerTests`.
Startup/DI evidence is under `Startup`, including `HostCompositionTests`.

ControllerBoundaryTests uses a pending/failing service through real ASP.NET creation
routes (Item, Action, nested Action). It observes actual RequestAborted propagation
and safe public failures without duplicating business-rule matrices. A disconnected
caller has no promised HTTP status. Existing CRUD tests retain Location, ownership,
validation and empty-response evidence. ProblemWriterBoundaryTests uses real AddApi
registration, ProblemDetailsService and JSON response behavior; it is not a fake
ProblemDetailsService unit test moved without a new boundary.

## Infrastructure safety

- PostgreSQL tests use dedicated TEST infrastructure. PostgresFixture requires the base database name `goalstats_template_test` and creates generated databases for cases; never reuse LOCAL/DEV databases or delete their volumes. The dedicated user must be able to create/drop its owned test databases.
- Redis tests use unique prefixes/keys and targeted cleanup. Never use `FLUSHALL` or `FLUSHDB`; remove only keys owned by the test, even on failure.
- Dispose factories, connections, transactions, proxies and pending operations. Fault only owned resources; do not stop a shared Redis/PostgreSQL server to simulate an outage.
- Use bounded waits and deterministic signals. Observe the relevant operation/lock before triggering cancellation or recovery rather than relying on scheduler speed.
- Avoid process-global environment mutation. Use factory configuration overrides and scoped child-process environments so parallel tests do not reconfigure each other.
- Do not mix LOCAL/DEV/TEST ports, database names or volumes. The normal scripts create unique disposable Compose projects and clean only their resources. Follow [operational TEST guidance](DEVELOPMENT.md#test-overview) for credentials and failure cleanup.

## Commands

All commands run from the repository root in the [supported shell/setup](DEVELOPMENT.md#shell-and-working-directory).
Normal Make tests require Docker/Compose and Make, not host .NET. SDK 8.0.303 and
pinned EF tooling run inside the Dockerfile tooling image. Smoke/certification
additionally need host Python 3. Leave SERVICE_WORKFLOW_CERTIFICATION unset normally.

| Purpose | Preferred command | Raw mechanism / evidence |
| --- | --- | --- |
| Fast unit feedback | `make unit` | `dotnet test tests/GoalStats.Template.Api.UnitTests/GoalStats.Template.Api.UnitTests.csproj` in a network-disabled SDK container; isolated behavior, no providers |
| Integration only | `make integration` | `./scripts/test.sh integration`; provisions real TEST PostgreSQL/Redis, runs only integration csproj, cleans up |
| Full automated suite | `make test` | `./scripts/test.sh`; provisions TEST, runs unit + integration solution, cleans up |
| Actual image smoke | `./scripts/smoke.sh` | `./scripts/smoke.sh`; explicit migrations, root Dockerfile build, Staging image, Healthy liveness/readiness, Swagger UI/JSON, Item/Action CRUD/cache reads/cascade, cleanup |
| LOCAL/DEV workflow certification | `python3 scripts/certify-workflows.py` | `python3 scripts/certify-workflows.py`; actual topologies, persistence, isolation, failure/interruption and cleanup |
| Hosted tests without providers | Direct dotnet command | `dotnet test GoalStats.Template.sln --filter "Category!=Postgres&Category!=Redis"` |

The first three rows are the normal public Make test interface; smoke/certification are advanced scripts. Normal inner-loop logic work
uses unit tests; provider/HTTP changes use integration; full regression uses test.
Image/startup changes warrant smoke. Workflow/environment changes or template-level
certification warrant certify; it is not required for every edit.

Use `--filter FullyQualifiedName~YourTestName` with a `dotnet test` project command
for a focused regression. Filters do not supply missing infrastructure. The scripts
are the normal full-suite/image entry points; `test.sh` accepts only optional `all` (default), `unit`, or `integration`,
not arbitrary `dotnet test` arguments.

### Certified MetaController baseline

Before production edits, 28 focused characterization/surface/OpenAPI cases passed
against the startup mappings. After replacement, the same transport assertions plus
startup configuration checks passed (36 cases); the focused provider run passed all
12 cases. Solution build passed with 0 warnings and 0 errors.

`make unit`, `make integration` and `make test` passed with 260 unit / 293 integration /
553 total, 0 failures and 0 skips. Compared with the previous certified 260 / 276 /
536 baseline, the change adds 17 integration cases: 4 selection/aggregation, 8 method,
4 Accept and 1 request-abort case. The 2 original PostgreSQL endpoint cases moved
without removal, and endpoint ownership assertions expanded an existing test.
Counts describe observed discovery, not a permanent target.

Full certification passed in a fresh disposable macOS clone of the canonical
remote with the intended changes applied. The candidate independently passed setup,
unit/integration/full suites at the same counts, solution build (0 warnings / 0
errors), API publish and EF checks for TemplateDbContext and
`20260908043250_InitialCreate`, with no pending model changes.

Real Kestrel HTTP comparisons against the unchanged pre-MetaController baseline
passed all 72 combinations: both routes, GET/HEAD/POST/OPTIONS, three Accept values,
and Healthy/Redis-Degraded/PostgreSQL-Unhealthy states. Status, exact body bytes,
content type, anti-cache headers and content-length behavior matched. HEAD had an
empty wire body in both versions. Real Redis outage retained 200 `Degraded`; real
PostgreSQL outage retained 503 `Unhealthy`; liveness remained 200 `Healthy`.

LOCAL Development and DEV Staging passed public Make build/migrate/run/stop/restart,
Swagger, Item/Action CRUD/cache/cascade and persistence checks. DEV had no source
mounts. Unmodified smoke and workflow scripts passed normal execution, two controlled
failures per script and SIGTERM cleanup; LOCAL/DEV sentinel rows survived. Final
container/network/volume/image-tag inventories matched the starting inventory.
Provider code, registration/tags, migrations, Item/Action and runtime scripts are
unchanged. The narrow certification test update explicitly includes an untagged
failing check alongside a differently tagged check, proving both are excluded.

The earlier certification below predates MetaController.

### Previous certified baseline and historical counts

These are certified results for the test architecture alignment, not permanent
count requirements. All discovered cases must pass with no unexplained skips.

| Suite | Historical baseline | Certified baseline |
| --- | ---: | ---: |
| Unit | 304 | 260 |
| Integration | 271 | 276 |
| Total | 575 | 536 |

`make unit`, `make integration` and `make test` all passed in the working checkout
and a disposable fresh macOS candidate cloned from the canonical remote with the
intended changes applied. Both runs agreed on 0 failures and 0 skips. The eight
focused controller/writer replacement cases also passed without provider access
during alignment.

The fresh candidate passed setup, solution build (0 warnings / 0 errors), API
publish and EF checks for `TemplateDbContext` and
`20260908043250_InitialCreate`, with no pending model changes. Public Make
build/migrate/run/stop/restart workflows passed for LOCAL (Development) and DEV
(Staging, built runtime without source mounts), including Swagger, health/readiness,
Item/Action CRUD, cache invalidation, cascades and persistence.

The existing smoke and workflow certification scripts passed. LOCAL/DEV sentinel
rows survived normal TEST/smoke runs, two controlled failures per script and SIGTERM
cleanup. Before/after container, network, volume and image inventories matched;
only certification-owned resources were used. Production source, schema, HTTP/cache
contracts, runtime topology, Make interface and template identity remain unchanged.

The unit delta is 304 − 39 controller cases − 8 handler cases + 3 pure cleanup
cases = 260. The integration delta is 271 + 6 hosted controller cases + 2 real
writer-boundary cases − 3 pure cleanup cases = 276.

Of the removed coverage, 6 controller methods / 15 cases and 1 handler theory /
6 cases duplicated existing boundary evidence. The remaining 3 controller methods /
24 cases became 2 hosted theories / 6 cases proving request abort, safe service
failure and nested ownership. The 2 unique writer cases were rewritten against
real framework boundaries; the 3 pure cleanup cases moved to unit. Startup,
real database fixture failure and Redis proxy observation moves preserve their
case counts. The total decrease of 39 reflects consolidation, not a coverage target.

### TEST credentials and cleanup

`.env.test` is **optional** for `make integration`, `make test` and `./scripts/smoke.sh`.
No manual TEST Compose startup is needed. The scripts use disposable credentials
`service` / `change_me_test_only` when absent. If customization is needed, copy
`.env.example` to `.env.test`; only POSTGRES_USER and POSTGRES_PASSWORD are read,
using unquoted letters/digits/underscore/dot/dash. The scripts do not execute it.
The file is ignored by Git/Docker and is not created by `make setup`.

All test modes share `scripts/test.sh` provisioning and cleanup: database
`goalstats_template_test`, unique Compose project, ephemeral loopback ports and container-network connections. Unit does not provision providers. Integration-only selects the integration csproj; the default
runs GoalStats.Template.sln. Test fixtures create/migrate/drop generated case databases;
Redis cases use targeted keys. No LOCAL/DEV connections are reused.

Exit 0 means the selected run and cleanup succeeded. Failures stay nonzero; cleanup
failure also makes a successful run fail. EXIT/INT/TERM traps clean owned resources;
nonzero runs emit bounded logs. Each run removes its SDK container/image tag; smoke also removes its own API container/image. Docker build caches may remain.
An uncatchable kill or Docker daemon failure can prevent cleanup: recover only the
reported owned project, never delete unrelated LOCAL/DEV resources.

### Direct integration prerequisites (optional host SDK / IDE)

Prefer `make integration` (integration only) or `make test` (full solution) for
provision/run/cleanup in one command. For direct
integration execution or IDE debugging, provision **dedicated TEST** PostgreSQL
and Redis first, then export `ConnectionStrings__Postgres` (base database exactly
`goalstats_template_test`, user able to create databases) and `ConnectionStrings__Redis` into
the test process. PostgresFixture creates/migrates case databases; no LOCAL database
migration is needed. Ordinary ApiFactory does not import shell configuration, so
provider tests explicitly consume these connections through their fixtures/helpers.

The following optional Bash subshell gives a focused run its own TEST project and
ephemeral ports, without changing your parent shell's environment. It needs Docker
Compose v2 or newer and uses disposable example credentials; stop on any provisioning failure.
For an IDE session, arrange equivalent dedicated resources and exports for the IDE,
retain them while debugging and clean only that session's project afterward.

```bash
(
  set -euo pipefail
  export POSTGRES_DB=goalstats_template_test POSTGRES_USER=service POSTGRES_PASSWORD=change_me_test_only
  export POSTGRES_PORT=0 REDIS_PORT=0
  test_project="goalstats-template-test-manual-$(uuidgen | tr '[:upper:]' '[:lower:]')"
  test_compose=(docker compose --env-file /dev/null -p "$test_project" -f docker/compose.test.yml)
  trap '"${test_compose[@]}" down -v --remove-orphans' EXIT
  "${test_compose[@]}" up -d --wait --wait-timeout 60
  test_postgres_port=$("${test_compose[@]}" port postgres 5432)
  test_redis_port=$("${test_compose[@]}" port redis 6379)
  export ConnectionStrings__Postgres="Host=127.0.0.1;Port=${test_postgres_port##*:};Database=goalstats_template_test;Username=service;Password=${POSTGRES_PASSWORD}"
  export ConnectionStrings__Redis="127.0.0.1:${test_redis_port##*:}"
  dotnet test tests/GoalStats.Template.Api.IntegrationTests
)
```

This optional recipe also requires host `uuidgen` and `tr`. Its `down -v` targets
only the randomly named TEST project created inside the block. Do not substitute
a LOCAL/DEV project name. The maintained scripts provide broader signal handling
and failure logs; use them for routine certification.

### Workflow certification scope

Workflow certification is **not the normal inner loop**. Run it when changing
workflow/environment infrastructure or before certifying template-level changes.
It uses actual LOCAL/DEV Compose files, checks persistent rows across recreation,
and keeps those workflows alive while verifying TEST/smoke normal, controlled
failure and SIGTERM cleanup. It refuses occupied documented ports rather than
stopping unrelated processes. It does not prove cleanup after an uncatchable kill.

See [workflow certification operations](DEVELOPMENT.md#workflow-certification) for
port prerequisites, checkpoints, exit statuses and retained artifacts. Use
[troubleshooting](DEVELOPMENT.md#troubleshooting) for setup failures and the
[contributor checklist](DEVELOPMENT.md#contributor-checklist) to choose checks based
on your change. Passing unit tests alone does not certify HTTP, schema or real Redis
behavior; passing smoke alone does not replace the suite's detailed cases.
