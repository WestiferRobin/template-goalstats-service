# Certification and CI

`make certify` runs the complete repository workflow:

1. Ruff lint/format checks and strict mypy.
2. Provider-free tooling tests.
3. Disposable LOCAL/DEV runtime, migrations, persistence, and outage checks.
4. One successful pytest smoke run against built DEV Gunicorn.
5. One application unit/integration coverage run on isolated TEST providers.
6. Intentional unit-runner, integration-runner, migration, provider-startup, and
   pytest smoke assertion failures, with owned-resource cleanup assertions.
7. SIGTERM and SIGINT while a real TEST runner is active.
8. Developer-like row/cache marker survival and unrelated Docker resource preservation.

`scripts/validation/certify_workflows.py` owns workflow assertions. It checks repeated
upgrades, downgrade/re-upgrade and model drift, runtime UID, DEV without source
mounts/debug, clean Gunicorn exit, strict readiness, and persistent DB data across
stop/start. LOCAL uses the reload command and read-only source mount. A disposable
sentinel container/network/volume must survive other workflows, then is removed by
its owner. Existing Docker resources must remain; build images/cache may accumulate.

Failure injection deliberately invokes real failing processes. Missing required
pytest plugins exercise runner failure propagation; a missing HTTP route produces
an actual smoke assertion failure. Those expected failures do not mean the normal
application suite passed falsely. Normal application/smoke results are checked
separately. No global Docker prune is used.

The GitHub Actions workflow uses Python 3.12 on Ubuntu, runs `make setup`,
`make doctor`, and `make certify`. Docker installs the single requirements file;
YAML does not duplicate tests or provider orchestration. No secrets or deployment
credentials are needed. All validation providers belong to disposable projects.
The job has a bounded timeout; hosted-runner teardown handles machine-level loss.

Final release certification must independently repeat the checks from a fresh
checkout and review Git status, migration history, identity anchors, and remote
`legacy/dotnet` before publication. Passing this local workflow does not itself
commit, push, or certify a future published SHA.

## Automated host certification and manual IDE acceptance

From a fresh candidate containing only intended files:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
make certify-host PYTHON=.venv/bin/python
make check
make unit
make integration
make test
make migration-check ENV=local
make smoke
make certify
```

The migration-check target requires the candidate's own configured/migrated LOCAL
providers; do not select a developer's stack as disposable certification infrastructure.
The automated host certifier instead uses a unique disposable LOCAL project and
runs the same Alembic check there. All certification app/provider ports are dynamic.

`scripts/validation/certify_host.py` verifies Python 3.12/.venv, dependency consistency,
Docker-free unit suite/folder/file/node execution, smoke-free collection, portable
VS Code JSON, provider-only startup, host PostgreSQL/Redis connections, migrated
readiness, direct main health and Item CRUD, persistence across provider stop/start,
no child/reloader process, active full LOCAL protection, owned TEST individual
repository/migration/Redis tests, stale/mismatched endpoint refusal, SIGINT/SIGTERM
cleanup, and before/after resource equality (except retained build images/cache).
Provider-free tooling tests exercise tampered ownership and unsafe env-file cases.
No business schema or migration history is changed.

Automated success means **READY FOR MANUAL IDE VERIFICATION**. Prompt 3 must exercise
actual PyCharm Run/Debug and VS Code F5, verify breakpoints at `main`, router, service,
repository and cache, and exercise IDE discovery and individual test selection.
Do not report actual IDE debugger/discovery acceptance from CLI tests alone.

Zero-friction startup acceptance uses an exact disposable source copy and its actual
repository `.env.local`; the developer's private file is never replaced. It
launches bare main with application variables removed, from root and `src/` cwd.
Unit tests cover private-file parsing, contradictory modes, precedence, loopback,
provider diagnostics, occupied ports, and factory/import isolation. Actual IDE Run
must use no env-file profile; command-line acceptance never implies breakpoint acceptance.
