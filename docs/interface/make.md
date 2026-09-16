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

`setup` preserves existing files. `doctor` only diagnoses. `run` requires an already
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
