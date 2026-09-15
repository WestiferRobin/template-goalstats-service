# GoalStats Flask service template

Python **3.12**, Flask, synchronous SQLAlchemy/PostgreSQL, Alembic,
Marshmallow/flask-smorest, Redis, and pytest. Item + Action demonstrate the service
architecture; there is no User/authentication domain.

## Prerequisites and quick start

Install Docker with Compose v2 or newer (Docker Desktop on macOS), GNU Make, and
Python 3.12 for host workflow scripts. Start Docker before setup. Docker supplies
all application dependencies; a host virtual environment is optional.

```sh
make help
make setup
make build ENV=local
make migrate ENV=local
make run ENV=local
```

Open LOCAL at <http://127.0.0.1:5100/swagger>. Its Flask development server reloads
mounted `src/` changes; the interactive debugger is disabled. Rebuild after changing
dependencies or migrations. `run` never generates or applies migrations.

```sh
make build ENV=dev
make migrate ENV=dev
make run ENV=dev
```

DEV serves <http://127.0.0.1:5200/swagger> using two Gunicorn workers from the built
image, with no source mount and debug disabled. Rebuild after source changes.
Both servers bind published ports to loopback. PostgreSQL/Redis have no host ports.

```sh
make logs ENV=local
make stop ENV=local
make stop ENV=dev
```

Stop removes only the selected Compose containers/network and **retains its database
volume**. Redis is ephemeral and is empty after container recreation. LOCAL/DEV use
separate projects, databases, volumes, Redis containers, and cache prefixes. No old
.NET resource identities are reused. Unknown `ENV` values are errors.

## Configuration and dependencies

`make setup` verifies tools/Docker and creates missing `.env.local` and `.env.dev`
with randomly generated database passwords and default ports. It uses exclusive
creation with mode 0600 and never overwrites existing values or starts a stack.
Only `POSTGRES_PASSWORD` (16–128 URL-safe letters/digits/underscore/hyphen) and
`APP_PORT` are accepted in those files. They are ignored by Git and excluded from
Docker builds. Changing a password does not rotate an existing PostgreSQL volume's
password; preserve the existing value or deliberately administer that database.

`.env.example` documents both the Compose input and direct application settings.
The app does not implicitly load dotenv files. Compose supplies fixed identities
and explicit application settings, ignoring ambient application URLs.

**DEPENDENCY FILES: requirements.txt ONLY**

Direct and transitive dependencies are pinned in this one file, including Gunicorn
and locally served Swagger assets. Images use digest-pinned official Python 3.12,
PostgreSQL 17, and Redis 7.4 bases. For optional host development:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --no-deps -r requirements.txt
.venv/bin/python -m pip check
PYTHONPATH=src .venv/bin/python -m pytest tests/unit
```

The Docker build installs that same file with `--no-deps` and checks dependency
closure. Update direct and transitive pins together and rebuild/test both supported
development environments. The simple image intentionally includes quality/test
packages from the single dependency file; the runtime stage contains only app and
migration source. Never commit the virtual environment.

## Tests and quality

```sh
make unit          # no providers; container network disabled
make integration   # unique disposable TEST PostgreSQL + Redis
make test          # unit + integration exactly once
make coverage      # full suite; terminal report, no arbitrary percentage gate
make check         # Ruff lint, formatting check, strict mypy; no source edits
make smoke         # HTTP smoke against a disposable built DEV stack
make certify       # LOCAL/DEV persistence, isolation, failure/signal cleanup
```

Test targets rebuild the tooling image as necessary. TEST providers use memory-backed
storage, private Compose networking, and unique project names. Migrations run before
integration tests. Success, failures, SIGTERM, and SIGINT trigger cleanup of only
owned disposable resources. Coverage data stays inside the removed runner container.
`smoke` and `certify` use unique disposable projects and ports; they never use your
LOCAL/DEV env files or delete your developer volumes. Their disposable volumes may
be removed because those scripts created them solely for certification.

Images/build cache remain available for subsequent commands; no command runs global
Docker prune. SIGKILL, machine shutdown, or Docker daemon failure cannot guarantee
cleanup: see [Development](docs/DEVELOPMENT.md) for scoped recovery.

## Migrations

```sh
make migrate ENV=local
make migrate ENV=dev
make migration MESSAGE="describe the schema change"
make migration-check ENV=local
make migration-check ENV=dev
```

Migration creation is LOCAL-only, requires a message, and deliberately mounts only
`migrations/` writable to create a revision owned by your host UID. Bring the database
to the current head first; review generated upgrade/downgrade operations, then apply,
check, test, and rebuild. There is no automatic commit or startup autogeneration.
The fresh Python initial revision is `b7f42e9c1a60`.

## API, health, and architecture

Swagger UI: `/swagger`. Generated OpenAPI JSON: `/swagger/v1/swagger.json`.
UI JavaScript/CSS are served locally from the pinned `swagger-ui-bundle` dependency;
no browser CDN access is needed. Set `OPENAPI_ENABLED=false` in direct deployments
to disable UI, assets, and specification together. Compose enables them explicitly.

| HTTP operation | Path |
| --- | --- |
| GET / POST | `/items` |
| GET / PUT / DELETE | `/items/<item_id>` |
| GET / POST | `/actions` |
| GET / PUT / DELETE | `/actions/<action_id>` |
| GET / POST | `/items/<item_id>/actions` |

Routes bind/validate HTTP, services own transactions and cache decisions, repositories
own SQLAlchemy persistence, and PostgreSQL enforces constraints/cascade deletion.
Redis is cache-aside with post-commit invalidation and a default 300-second TTL.
See [Architecture](docs/ARCHITECTURE.md) for schemas and consistency limits.

- `/health`: HTTP 200 `Healthy`, independent of providers.
- `/ready`: HTTP 200 `Healthy` with valid database/migration access and Redis.
- `/ready`: HTTP 200 `Degraded` with database ready but Redis unavailable.
- `/ready`: HTTP 503 `Unhealthy` with database/schema/migration access unavailable.

Docker health checks and startup waits require **200 plus exact `Healthy`**.
Operational endpoints are intentionally absent from the business OpenAPI spec.
Errors use safe `application/problem+json`; no debug traceback or provider secrets.

## Troubleshooting and scope

If startup fails, use `make logs ENV=...`, check Docker, apply `make migrate`, and
check the selected private env file. A port conflict requires changing `APP_PORT`.
Degraded means Redis needs attention; Unhealthy means inspect PostgreSQL/migration
state. `make stop` preserves data so retrying does not require a database reset.

Read [Development](docs/DEVELOPMENT.md) and [Testing](docs/TESTING.md) for exact
ownership, recovery, and validation behavior. Authentication, public deployment/TLS,
and application-specific domain behavior are outside this reference template.
Historical .NET work remains on `legacy/dotnet`; active instructions are Python only.
