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
