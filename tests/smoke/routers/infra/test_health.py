import pytest

pytestmark = pytest.mark.smoke


def test_built_system_liveness(smoke_client):
    path = "/deliberately-missing-smoke-route" if smoke_client.fault else "/health"
    assert smoke_client.request(path)[0] == "Healthy"
