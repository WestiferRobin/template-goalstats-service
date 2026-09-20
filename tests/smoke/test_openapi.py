import pytest

pytestmark = pytest.mark.smoke


def test_built_system_swagger_and_openapi(smoke_client):
    html, _ = smoke_client.request("/swagger")
    assert "/swagger/v1/swagger.json" in html and "/swagger-assets/" in html
    assert "https://" not in html and "http://" not in html
    js, _ = smoke_client.request("/swagger-assets/swagger-ui-bundle.js")
    assert "SwaggerUIBundle" in js
    spec, _ = smoke_client.request("/swagger/v1/swagger.json")
    assert set(spec["paths"]) == {
        "/items",
        "/items/{item_id}",
        "/actions",
        "/actions/{action_id}",
        "/items/{item_id}/actions",
    }
