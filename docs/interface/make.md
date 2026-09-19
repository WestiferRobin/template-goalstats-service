# Public Make interface

Make is the stable developer interface; Python owns process/resource orchestration.
The root Makefile defines shared variables and includes these modules:

| Module | Commands |
| --- | --- |
| `install.mk` | `setup` |
| `doctor.mk` | `doctor` |
| `dev.mk` | `build`, `run`, `stop`, `logs` |
| `db.mk` | `migrate`, `migration`, `migration-check` |
| `test.mk` | `unit`, `integration`, `test`, `smoke` |
| `coverage.mk` | `coverage` |
| `ci.mk` | `check`, `tooling`, `certify` |

`make help` groups the interface. `ENV=local` is the default; runtime/database
commands accept `ENV=local|dev` and reject unknown values. TEST is internally managed.
`PYTHON=python3.12` can select the host interpreter. Application dependencies are
installed in Docker from the one pinned `requirements.txt` using pip.

```sh
make setup
make doctor
make build ENV=local
make migrate ENV=local
make run ENV=local
make logs ENV=local
make stop ENV=local
make build ENV=dev
make migrate ENV=dev
make run ENV=dev
make stop ENV=dev
make migration MESSAGE="describe the change"
make migration-check ENV=local
```

`setup` creates `.env.local` and `.env.test`, preserves valid canonical files, and safely migrates legacy configuration. `doctor` only diagnoses. `run` requires an already
migrated database and never applies migrations. `stop` retains developer DB volumes.
`migration` requires LOCAL and a nonblank message; it writes to `alembic/` for review.

| Command | Exact test/quality scope |
| --- | --- |
| `unit` | `tests/unit`, network-disabled container |
| `integration` | `tests/integration`, disposable PostgreSQL/Redis |
| `test` | `tests/unit tests/integration`, one pytest invocation |
| `coverage` | Same application suite, terminal line coverage |
| `tooling` | `scripts/tests`, network-disabled container |
| `smoke` | `tests/smoke`, real built Gunicorn HTTP system |
| `check` | Ruff lint, Ruff format check, strict mypy; no source edits |
| `certify` | Quality + tooling + application coverage once + built smoke once + lifecycle checks |

Certification additionally induces failed runner/provider/migration/smoke operations
and signals to verify cleanup; these are expected negative scenarios, not repeated
successful suites. Commands propagate failures and do not stage, commit, or deploy.

## IDE DEVELOPMENT commands

| Command | Behavior |
| --- | --- |
| `providers ENV=local` | Start only healthy LOCAL PostgreSQL/Redis; verify bindings/auth; use canonical machine config; no app/migration |
| `providers-stop ENV=local` | Stop only providers; retain PostgreSQL volume, containers and network; refuse active full LOCAL app |
| `test-providers` | Foreground isolated disposable TEST session, dynamic loopback endpoints, private ownership manifest; Ctrl-C/SIGTERM cleanup |
| `certify-host PYTHON=.venv/bin/python` | Python 3.12 host acceptance after installing requirements; disposable providers, CRUD/persistence, individual tests, ownership/signal checks; no IDE UI claim |

`dev.mk` owns LOCAL provider targets, `test.mk` owns `test-providers`, and `ci.mk`
owns `certify-host`; Python orchestration implements them. Provider targets reject
`ENV=dev`. Normal `integration`, `test`, `migrate`, `smoke`, and `certify` retain their
existing workflows. Host certification is additive and allocates its own ports.
See the [README workflow](../../README.md#ide-development) for initial IDE setup.

After `providers ENV=local` and `migrate ENV=local`, run/debug `src/main.py` directly:
it loads the prepared host file without IDE environment configuration. No `make ide`
command is needed. Rebuild an existing image when dependencies or migrations change.
