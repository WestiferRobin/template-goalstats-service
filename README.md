# GoalStats Flask service template

Python 3.12, Flask/Gunicorn, PostgreSQL/SQLAlchemy/Alembic, Redis,
Marshmallow/flask-smorest, and pytest. Item + Action demonstrate the architecture.

## Prerequisites and setup

Install Python 3.12, GNU Make, and Docker with Compose v2; start Docker Desktop
on macOS. Application dependencies install in Docker from `requirements.txt`.

```sh
make help
make setup
make doctor
```

Setup creates only missing private `.env.local`/`.env.dev` files and preserves
existing values. These files are ignored by Git. Doctor is read-only.

## Run LOCAL or DEV

```sh
make build ENV=local
make migrate ENV=local
make run ENV=local
```

LOCAL reloads source; Swagger is at <http://127.0.0.1:5100/swagger>.

```sh
make build ENV=dev
make migrate ENV=dev
make run ENV=dev
```

DEV uses built non-root Gunicorn without source mounts; Swagger is at
<http://127.0.0.1:5200/swagger>. Rebuild after source/dependency/migration changes.
`run` never applies migrations. Ports can be changed in the private env files.

`make logs ENV=local|dev` shows logs. `make stop ENV=local|dev` removes that stack's
containers/network but preserves its PostgreSQL volume. Redis is ephemeral.

## Validate and migrate

```sh
make check
make unit
make integration
make test
make coverage
make tooling
make smoke
make certify
make migration MESSAGE="describe schema change"
make migration-check ENV=local
```

Application tests, tooling tests, and built-system smoke have separate ownership.
TEST/smoke/certification use disposable providers and preserve developer data.
Migration creation is LOCAL-only, writes to `alembic/`, and requires review.
No command stages, commits, pushes, or deploys.

**DEPENDENCY FILES: requirements.txt ONLY**

Optional host tooling: `python3.12 -m venv .venv`, then
`.venv/bin/python -m pip install -r requirements.txt`.

See the [documentation index](docs/README.md),
[architecture/API contracts](docs/service/architecture.md),
[developer workflow](docs/service/development.md), and
[Make interface](docs/interface/make.md).

## Flat source layout

Application modules live directly under `src/`: `main.py`, `composition.py`,
`enums/`, `exceptions/`, `settings/`, `models/`, `schemas/`, `infra/`, `services/`,
and `routers/`. The factory is `main:create_app()`; no intermediate service package
is present. See [template anchors and execution paths](docs/standard/template.md).
