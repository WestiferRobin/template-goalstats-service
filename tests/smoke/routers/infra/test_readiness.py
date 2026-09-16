import pytest

pytestmark = pytest.mark.smoke


def test_built_system_readiness(smoke_client):
    assert smoke_client.request("/ready")[0] == "Healthy"
