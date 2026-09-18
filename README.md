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

## IDE DEVELOPMENT

Host development is additive; all Docker commands above remain supported.

```sh
# once
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make setup

# providers (no app and no automatic migrations)
make providers ENV=local
make migrate ENV=local

# then: PyCharm → Run/Debug src/main.py; VS Code → Flask: host LOCAL
# Docker-free unit tests
.venv/bin/python -m pytest tests/unit
# canonical complete integration suite
make integration
# optional foreground session for IDE integration debugging
make test-providers
# stop providers, preserving PostgreSQL data
make providers-stop ENV=local
```

In PyCharm select `.venv/bin/python`, open `src/main.py`, and click Run/Debug.
No custom environment variables, env-file profile, or Flask configuration is needed.
Marking `src/` as Sources Root is optional editor assistance, not a runtime requirement.
In VS Code select the workspace `.venv` and **Flask: host LOCAL** (F5).
Both IDEs and `python src/main.py` use the same direct-only loader for the repository's
private `.env.host.local`, independently of working directory. The host server binds
`127.0.0.1:5300`; the IDE owns debugging. No reloader or built-in debugger is enabled.
The imported factory remains `main:create_app()` and never loads host configuration.

Rebuild after dependency or migration changes, then migrate for new revisions.
Host source edits need only an IDE restart; Docker DEV source edits require rebuild.
Reinstall requirements after dependency changes. See [IDE setup and safety](docs/service/development.md#ide-development)
and [owned integration debugging](docs/testing/overview.md#ide-integration-debugging).
