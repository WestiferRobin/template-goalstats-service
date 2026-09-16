# Reference architecture

```text
Route → Service → Repository → SQLAlchemy Session → PostgreSQL
              └→ Resource Cache → Redis JSON adapter → Redis

ORM entity → immutable scalar result → Marshmallow response schema → HTTP
```

The application factory explicitly constructs app-owned Engine/session and Redis
pools. Routes obtain services through the Flask composition boundary. Services,
repositories, and cache adapters do not depend on Flask globals. One requirements
file and Python 3.12 remain the dependency/runtime contract.

## Resource contracts

| Methods | Path | Behavior |
| --- | --- | --- |
| GET, POST | `/items` | List / create Item |
| GET, PUT, DELETE | `/items/<item_id>` | Read / update / delete Item |
| GET, POST | `/actions` | List / create Action with body `itemId` |
| GET, PUT, DELETE | `/actions/<action_id>` | Read / update / delete Action |
| GET, POST | `/items/<item_id>/actions` | List / create with parent from URL |

POST returns 201 plus canonical Location; Item Location is `/items/<id>` and either
Action creation form uses `/actions/<id>`. GET/PUT return 200; DELETE returns an
empty 204. Missing resources/parents return 404 Problem Details. An existing parent
with no children returns an empty list. There are no nested Action get/update/delete
routes. Requests reject unknown fields. Nested creation and Action update do not
accept `itemId`. Action's parent is immutable through this API.

Names are required, nonblank, and at most 200 characters. Names need not be unique.
Item status is `active` or `archived`; new Items are active. Action type is `create`,
`update`, or `delete`. Numeric and quoted-number enum values are rejected. IDs are
UUIDs; input UUID zero is rejected. Malformed UUID paths are routing 404s, while
invalid body UUIDs are validation 400s. Marshmallow fields convert to snake_case
Python attributes, UUIDs, and StrEnums. Services also validate direct calls.

Item JSON: `id`, `name`, `status`, `createdAt`, `updatedAt`.
Action JSON: `id`, `itemId`, `name`, `type`, `createdAt`, `updatedAt`.
No ORM state or relationship graphs are returned. Timestamps are UTC-aware; updates
preserve creation time and advance modification time, including unchanged PUTs.
Lists order by creation time and UUID as tie-breaker.

## Database and transactions

`items` has a UUID PK, required bounded/nonblank name, constrained string status,
and non-null timezone-aware timestamp columns. `actions` has the same core fields,
a constrained action type, and an indexed FK to `items` with ON DELETE CASCADE.
No Python-side cascade graph is needed. Alembic revision `b7f42e9c1a60` establishes
this fresh Python schema. Python supplies UUID/timestamp defaults on ORM insertion;
direct SQL writers must supply those values explicitly.

Each service operation owns a fresh transaction/session. Repositories can query,
add, delete, or flush, but do not commit. A successful context exit commits; any
failure rolls back and closes. Results are built inside the session; cache writes
or invalidation happen after successful exit. A failed flush/commit cannot trigger
successful mutation-related cache changes.

Update/delete lock their target rows. Action creation locks its parent before
inserting, serializing it with parent deletion; the database FK remains the final
relationship invariant. Overlapping operations may observe either legitimate
ordering. There is no generic repository, DI framework, or custom UnitOfWork class.

## Cache behavior

RedisCache owns bounded GET/SET/DEL, JSON, and safe failure logging. Resource caches
own `{prefix}:items:<uuid>` and `{prefix}:actions:<uuid>` keys, schema validation,
identity checking, and TTL (default 300 seconds). Prefixes separate services and
environments. Cache payloads use explicit scalar schemas, never pickle or ORM objects.

GET-by-ID is cache-aside; a miss queries PostgreSQL and fills Redis. Lists remain
uncached. Creation does not fill the cache. Update/delete invalidate after commit.
Malformed/incomplete/wrong-identity cache payloads are misses. Redis connection,
permission, or serialization failures do not invalidate successful PostgreSQL work.
Logs omit raw URLs, credentials, payloads, and provider error messages.

An Action cache hit still checks database row existence. If cascade deletion removed
it, the service discards the cached child and returns 404, even if Redis deletion
fails. Item deletion never scans child cache keys or couples itself to ActionCache.
This existence check is not atomic with overlapping deletions.

Cache and PostgreSQL are not one transaction. Failed invalidation or concurrent
cache fills can leave stale values until TTL expiry. The child check protects
absent Actions, not freshness of still-existing rows. Item cache hits do not query
the database. Do not claim stronger consistency than these guarantees.

## Operations and errors

`/health` is provider-independent liveness. `/ready` requires exact Alembic heads
and usable mapped columns; missing revision/table/column or unavailable PostgreSQL
is 503 Unhealthy. With PostgreSQL ready, a successful bounded Redis GET gives
200 Healthy; missing/unavailable Redis gives 200 Degraded. Consumers waiting for
startup must require 200 and Healthy. Full schema drift checks use Alembic, not
per-request schema autogeneration.

App-owned Redis resources are closed when their app/test/CLI owner is retired,
not at request teardown. Domain operations close their SQLAlchemy sessions. There is no request-scoped
session facility. Import
and factory construction never connect, migrate, seed, or call external APIs.

Safe Problem Details handlers own validation, domain, framework, and unexpected
errors. flask-smorest documents resource schemas, enum values, validation statuses,
canonical Location headers, and the shared Problem response. Meta paths are excluded.
Swagger is served at `/swagger` with local pinned assets and the generated spec at
`/swagger/v1/swagger.json`. LOCAL reloads source; DEV uses a non-root built Gunicorn
image; TEST owns disposable providers. See [Development](development.md) for runtime
identities and cleanup. No User or prediction domain is present.

## Prizm-derived package placement

| Package | Responsibility |
| --- | --- |
| `main.py` | Flask factory, app-owned resources, registration, OpenAPI |
| `composition.py` | Narrow Flask resource access and concrete service construction |
| `routers/item`, `routers/infra` | Domain and operational HTTP adapters |
| `schemas/item`, `schemas/action` | Immutable scalar results, request and response schemas |
| `schemas/infra` | Problem Details contract |
| `services/item` | Item/Action operations and direct-call validation |
| `services/infra.py` | Readiness policy |
| `infra/repositories` | Concrete session-bound SQLAlchemy queries and writes |
| `infra/caches` | Domain cache identity and serialization |
| `infra/resources` | Engine/sessionmaker and Redis ownership, readiness, disposal |
| `models/base.py` | The single authoritative SQLAlchemy Base and metadata |
| `enums` | ItemStatus and ActionType reference values |
| `settings` | Validated, instance-owned configuration |
| `exceptions` | Framework-independent errors and Flask HTTP translation |

All paths above are beneath `src/`. Dependencies flow from
routers through services to concrete infrastructure and model/contract definitions.
Services and infrastructure do not access Flask globals; composition is the
framework boundary. Caches consume domain contracts rather than importing services.

Prizm's domain router grouping maps to Flask Blueprints. Pydantic contracts map
to Marshmallow and immutable scalar records. FastAPI dependencies map to explicit
composition. Async lifespan machinery maps to app-owned resources and explicit
owner cleanup. Gunicorn serves WSGI. There are no generic provider registries,
authentication platform, queues, gRPC, async sessions, or dynamic router discovery.
Item and Action remain example domains, not a User-service implementation.
