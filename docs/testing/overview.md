# Test ownership

UNIT TESTS FOLLOW LOGIC

INTEGRATION TESTS FOLLOW BOUNDARIES

SMOKE TESTS FOLLOW BUILT SYSTEM

ROUTERS: INTEGRATION

Unit tests cover settings, schemas, service decisions, cache identity/payload logic,
and safe domain errors. Integration tests exercise Flask binding/OpenAPI/errors,
real PostgreSQL repositories/constraints/transactions, real Redis behavior, and
Alembic history. No route unit suite is maintained.

`tests/fixtures/` owns settings, app factories, disposable database/Redis fixtures,
named Item/service collaborators, and smoke clients. Root `conftest.py` registers
fixtures and gates smoke collection. There is no global provider registry.

Default pytest selects `tests/unit tests/integration`. Even explicit `pytest tests`
ignores the smoke directory unless `--smoke` is supplied. `make smoke` is the
supported built-system entrypoint: direct smoke selection additionally requires its
owned runtime configuration. Tooling tests live in `scripts/tests`; `make tooling`
and certification run them separately from application unit/integration ownership.

Provider fixtures require explicitly disposable resources. Missing provider URLs in
manual pytest runs produce explained skips; Make provisions providers, so canonical
integration/full/coverage runs must have zero skips. Invalid or unavailable supplied
providers fail. PostgreSQL uses a dedicated `goalstats_test_*` database; Redis cleanup
is limited to each fixture's unique prefix. No FLUSHALL or shared database fallback.
Use one provider pair per concurrent pytest process; xdist is not configured.

`make coverage` measures application unit/integration coverage only, inside the
removed TEST runner. Smoke is not used to inflate it. No 100% threshold is imposed.
Migration tests verify fresh upgrade, repeat safety, downgrade/re-upgrade, and
`alembic check`. Revision `b7f42e9c1a60` is preserved.

See [smoke](smoke.md), [certification](certification.md), and
[Make interface](../interface/make.md).
