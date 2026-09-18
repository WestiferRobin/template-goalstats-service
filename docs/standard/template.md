# Template ownership and identity

This is the canonical Flask Item + Action reference service. Its relevant package,
fixture, Make, script, and documentation conventions follow Prizm's Python template.
Flask Blueprints, explicit composition, Marshmallow, synchronous resources, and
Gunicorn intentionally replace FastAPI-specific mechanics.

Template-owned conventions include package responsibilities, configuration,
resource/transaction ownership, HTTP errors, test ownership, Make interface,
Docker safety, and certification. Generated services customize their actual domain
models/contracts/repositories/services/routers and corresponding tests/migrations.
Item + Action demonstrate that placement; do not silently turn Item into User.

Architecture changes should be promoted into this template first, certified here,
then deliberately adopted into generated services. This repository does not edit
parent scaffolding or other repositories. Legacy .NET stays archived on
`legacy/dotnet`; active runtime/dependency instructions are Python only.

## Stable scaffold anchors

| Identity | Current value |
| --- | --- |
| Repository | `template-goalstats-service` |
| Source/import root | `src/` (flat modules; no service package directory) |
| Coverage source | `src` |
| Factory | `main:create_app()` |
| Image/runtime slug | `goalstats-template-py` |
| Image tags | `goalstats-template-py:runtime`, `goalstats-template-py:tooling` |
| Developer Compose projects | `goalstats-template-py-local`, `goalstats-template-py-dev` |
| Disposable projects | `goalstats-template-py-test-<hex>`, `goalstats-template-py-cert-<hex>` |
| Developer databases | `goalstats_template_py_local`, `goalstats_template_py_dev` |
| TEST database | `goalstats_test_runtime` |
| Cache namespace | `goalstats-template-py:<env>:v1` |
| API display title | `GoalStats Template API` |
| Logger identity | `goalstats_template` (service label, not an import/package) |
| Internal Compose services | `app`, `runner`, `postgres`, `redis` |
| Disposable tool container | `goalstats-template-py-tool-<hex>` |
| CI concurrency | `goalstats-template-${{ github.workflow }}-${{ github.ref }}` |

Later scaffolding must update identity producers, consumers, safety guards, fixtures,
Docker/Compose references, and observations together. There is no Python package-directory identity to transform. Flat module names,
source paths, the Item/Action reference domain and generic `goalstats_*` extension
keys remain unchanged.
Do not use broad textual substitution. The migration revision is not an identity
placeholder: preserve `b7f42e9c1a60` unless a separately reviewed migration is needed.

Dependencies remain Python 3.12 and one pinned `requirements.txt`. No generic
provider framework, async architecture, authentication platform, queues, or gRPC
is included. PostgreSQL and Redis are the only runtime providers.

## Flat Python execution contract

`src/main.py` exports `create_app`; `src/composition.py` wires concrete resources
and services. Modules import directly from `enums`, `exceptions`, `settings`,
`models`, `schemas`, `infra`, `services`, `routers`, and `composition`. There is no
intermediate service package and no `src` package to import.

Pytest declares `pythonpath = src scripts`; Alembic uses its configuration-relative
`prepend_sys_path`; mypy declares `mypy_path = src`. Docker explicitly sets
`PYTHONPATH=/app/src`, shared by Gunicorn, LOCAL Flask CLI, migration/test runners
and certification subprocesses. CI calls the same Make/Docker workflows. Host
factory commands must explicitly expose the source directory, for example
`PYTHONPATH=src flask --app 'main:create_app()' run`. No developer shell path
configuration is assumed by the public Make workflows.

The remaining `goalstats_template` occurrences are intentional service identities:
LOCAL/DEV database names (and their producers/ownership checks) and the isolated
application logger label. They are not Python package references. Generic TEST
identities and unrelated-resource sentinels remain intentionally generic.

## Host development and propagation

Host IDE support is additive to Docker. Flat `src/`, `main:create_app()`, Python 3.12,
one `requirements.txt`, Item/Action behavior, HTTP/OpenAPI, database schema/migration
history, Redis semantics and health/readiness contracts stay unchanged. Direct
`src/main.py` adds only a LOCAL development entrypoint. `src/` is not a package;
script execution naturally exposes it, pytest uses its configured paths, Alembic
uses its existing prepend path, and Docker/Gunicorn use their existing PYTHONPATH.

Track only portable `.vscode/settings.json`, `.vscode/launch.json`, and optional
`.vscode/extensions.json`. Ignore `.idea/`, `.venv/`, `.env.host.local`, and
`.host-sessions/`. No extra dotenv example or dependency manifest is introduced.

Prompt 2 must extend the parent's exact `scripts/scaffold-transform.py:IDENTITY_PATHS`:

- Database identities `goalstats_template_py_local` / `goalstats_template_py_dev`:
  add `scripts/host_development.py` to their prefix's exact allowlist.
- `goalstats-template-py`: add `scripts/host_development.py`,
  `scripts/test_ownership.py`, and `scripts/tests/test_host_development.py`.

Existing allowed paths cover remaining identity occurrences. Shared VS Code files
and the host certification module contain no service identity. Generic TEST database,
receipt/session labels and extension keys stay unchanged. The existing path policy
accepts portable VS Code JSON and rejects any new `.env.*` example; retain `.env.example`
as the only tracked env source. Strengthen parent artifact rejection for `.idea/`
and `.host-sessions/`, and restrict `.vscode/` payloads to the three portable files.
Add transformation/contract tests for these identity paths, exact host entrypoint,
provider commands, ownership guard and portable IDE files; update the independent
scaffold fixture/golden expectations and parent development contract accordingly.
After certification/publication authorization, update the parent's canonical template
SHA and approved pins in the later prompts. No parent or User changes occur here.

Direct `src/main.py` means LOCAL host development. The service-neutral
`src/settings/host.py` loader belongs only to that entrypoint; the factory, Docker,
Alembic and tests remain independent. Portable VS Code app launch must not inject
an env file; PyCharm Python script Run needs no environment profile. Scaffold guards
must validate this shared loader and preserve its source bytes without identity rewrites.
