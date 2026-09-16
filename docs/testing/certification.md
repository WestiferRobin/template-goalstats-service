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
