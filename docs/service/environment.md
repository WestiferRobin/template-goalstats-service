# Environment configuration

There are two human-facing files per service, both ignored and private:

- `.env.local`: machine credentials, ports and LOCAL/DEV preferences.
- `.env.test`: TEST policy only. It cannot specify provider endpoints or ownership.

`make setup` creates missing files. Never copy an example or enter credentials in
an IDE. The authoritative keys, defaults and validation live in
`src/settings/environment.py`; application validation remains in `settings/base.py`.
Setup preserves valid existing bytes. Invalid files fail without credential logging.

## One machine configuration

Direct `src/main.py` reads repository `.env.local` independently of cwd and derives
LOCAL loopback URLs. Docker LOCAL derives `postgres:5432` and `redis:6379` URLs from
the same credentials. DEV uses its separate password, app port, project and volume
from the same machine file. Runtime mode is not a configuration filename.

The machine file stores no database/Redis URLs or service identities. Database names
and cache prefixes come from service code. Port defaults remain host app 5300,
Docker LOCAL 5100, Docker DEV 5200, PostgreSQL 55432 and Redis 56379. All published
LOCAL provider ports bind loopback. DEV and ordinary TEST providers are unpublished.

The direct loader never changes `os.environ`. Approved process overrides are
validated; contradictory modes and non-loopback host endpoints are refused. The
factory, Alembic and tests never implicitly read machine configuration.

## TEST policy and ownership

`.env.test` permits only logging, OpenAPI and cache TTL policy. Missing policy uses
code defaults; malformed existing policy fails. Unit tests require neither file.
CI and complete Docker integration workflows generate disposable credentials and
runtime configuration rather than reading developer endpoints.

`make test-providers` owns an optional foreground disposable debugging session.
Its private JSON manifests and lease under `.host-sessions/` are internal state,
not another env file. Run an integration test normally in either IDE while exactly
one session is active. Fixtures verify both providers before connecting. Multiple,
stale or mismatched sessions fail closed. Collection performs no Docker discovery.
Never use LOCAL providers for destructive integration tests.

## Existing installation migration

Run `make setup`. Legacy LOCAL/DEV passwords and ports are preserved separately.
Legacy host values must agree with derived identity/connection values; supported
preferences are preserved. Conflicts or failed authentication preserve the original
files. Existing volumes without credentials require restoration, never a new password.
After validation, setup writes canonical files privately and retains recoverable
original files under ignored internal migration state before retiring legacy files.
Changing a password in configuration does not rotate an existing PostgreSQL volume.
Never delete a data volume to resolve a configuration mismatch.

Generic dotenv discovery and production/cloud configuration are not part of this project.
