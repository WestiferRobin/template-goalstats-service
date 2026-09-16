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
| Python package/import/coverage | `goalstats_template` |
| Factory | `goalstats_template:create_app()` |
| Image/runtime slug | `goalstats-template-py` |
| Image tags | `goalstats-template-py:runtime`, `goalstats-template-py:tooling` |
| Developer Compose projects | `goalstats-template-py-local`, `goalstats-template-py-dev` |
| Disposable projects | `goalstats-template-py-test-<hex>`, `goalstats-template-py-cert-<hex>` |
| Developer databases | `goalstats_template_py_local`, `goalstats_template_py_dev` |
| TEST database | `goalstats_test_runtime` |
| Cache namespace | `goalstats-template-py:<env>:v1` |
| API display title | `GoalStats Template API` |

Later scaffolding must update identity producers, consumers, safety guards, fixtures,
Docker/Compose references, and observations together. Package identity is separate
from the Item/Action reference domain and generic `goalstats_*` extension keys.
Do not use broad textual substitution. The migration revision is not an identity
placeholder: preserve `b7f42e9c1a60` unless a separately reviewed migration is needed.

Dependencies remain Python 3.12 and one pinned `requirements.txt`. No generic
provider framework, async architecture, authentication platform, queues, or gRPC
is included. PostgreSQL and Redis are the only runtime providers.
