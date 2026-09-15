# Developer workflow

`Makefile` delegates to `scripts/workflow.py`, a standard-library Python orchestrator.
It owns configuration parsing, Compose selection, child process handling, readiness,
and cleanup. There is no duplicated shell workflow or dotenv shell evaluation.
`make help` groups setup, runtime, database, test, and quality commands.

## Environment identity

| Property | LOCAL | DEV | TEST |
| --- | --- | --- | --- |
| Project | `goalstats-template-py-local` | `goalstats-template-py-dev` | `goalstats-template-py-test-<random>` |
| APP_ENV | `local` | `dev` | `test` |
| Database | `goalstats_template_py_local` | `goalstats_template_py_dev` | `goalstats_test_runtime` |
| Storage | project `postgres-data` volume | separate project `postgres-data` volume | tmpfs |
| Redis | own container, tmpfs | own container, tmpfs | own container, tmpfs |
| Cache prefix | `goalstats-template-py:local:v1` | `goalstats-template-py:dev:v1` | `goalstats-template-py:test:v1` |
| Host API port | 5100 | 5200 | none |
| Runtime | Flask reload, read-only source mount | built Gunicorn, no mounts | tooling runner |

The TEST database name/prefix can repeat because every run has an independent
provider pair and network. Provider fixtures additionally use unique Redis prefixes.
Both persistent stacks have completely new Python identities. PostgreSQL 17 and
Redis 7.4 versions/digests are shared across all three Compose files.

## Setup and normal development

Run `make setup` twice safely: existing files and values are preserved. It verifies
Docker/Compose, Make and host Python, creates only missing private environment files,
and prints next steps. It starts no containers and modifies no application source.
Build, migrate, then run the selected stack. DEV uses two synchronous Gunicorn workers,
30-second request timeout and 10-second graceful shutdown, with a 15-second Compose
stop grace period and an init process for signal forwarding/reaping.

The LOCAL server enables source reload without the browser debugger. Only `src/`
is mounted and it is read-only; editing the host files triggers reload. Migrations and
dependencies are built artifacts, so rebuild after changing them. DEV always runs
its built copy of source. `make logs` prints the last 100 lines of selected services.

Ordinary `run` does not migrate. Ordinary `stop` uses the exact selected project and
never passes `--volumes`. Starting after stopping reconnects to its persistent data.
Redis has no persistence; losing cache entries is safe. Do not store durable state there.

## Migration review

`make migrate ENV=...` starts selected providers and runs `alembic upgrade head` in
a one-off image container. `make migration-check ENV=...` runs `alembic check` and
returns nonzero for model drift or unavailable database. `make migration MESSAGE="..."`
requires LOCAL and a nonblank message, passes the message as an argument (never shell
code), and autogenerates a revision through a deliberate writable migration mount.
Review it, run upgrade/check and tests, and rebuild before DEV. No revision is committed
automatically. Never edit an already published migration to rewrite history.

## Disposable workflow ownership

TEST uses unique project names, generated transient passwords, no published provider
ports, and tmpfs. Application/Compose environment values from the calling shell do
not select a developer database. One-off pytest containers have explicit TEST URLs
and disposable flags. The orchestrator terminates/reaps its CLI child on interruption,
then removes its project containers/network/volumes in `finally`, preserving failures.
Cleanup itself temporarily ignores a second SIGINT/SIGTERM.

`make smoke` creates a unique DEV certification project and deletes its volume in
`finally`. `make certify` creates unique LOCAL/DEV certification projects, verifies
persistence through stop/start, and checks TEST cannot alter their rows/cache markers.
Only these deliberately disposable certification volumes can be deleted by the
script. Existing developer configuration and volumes are not used.

The certification script snapshots Docker containers/images/networks/volumes and
compares afterward; existing resources must survive. It also creates an unrelated
sentinel container/network/volume and proves they survive failed TEST runs. That
sentinel is removed only by its creating owner at the end. Built images and build
cache are retained for reuse. No system/volume prune is implemented.

## Interrupted recovery

SIGTERM/SIGINT are covered; SIGKILL, host crashes, or Docker daemon outages may
interrupt any cleanup. First restore Docker. Inspect the exact project label:

```sh
docker ps -a --filter label=com.docker.compose.project=EXACT_PROJECT
```

Check that the name is your abandoned `goalstats-template-py-test-<random>` or
`goalstats-template-py-cert-<random>` run and is not active in another terminal.
Use the matching Compose file and exact `-p` identity to run `down --volumes` only
for that confirmed disposable run. Compose requires a placeholder URL-safe
`POSTGRES_PASSWORD` during interpolation even for down; it does not need the old
password to remove those resources. Never apply volume removal to LOCAL/DEV projects
containing developer data. Never use global prune as recovery.

## Formatting and dependencies

`make check` checks Ruff lint/format and strict mypy without modifying source.
For intentional host formatting after installing requirements, run
`.venv/bin/ruff format .`. Keep all direct/transitive pins in `requirements.txt`.
Digest and package updates are deliberate maintenance, followed by rebuild, pytest,
smoke and certification. No second requirements file or Python packaging manager is used.

For a manual certification of the default Make command path, first record that its
env files and LOCAL/DEV project resources do not exist. Only in that case may the
operator remove the exact volumes/configuration created solely by that certification
run after checking ownership. Pre-existing developer resources must be preserved.
