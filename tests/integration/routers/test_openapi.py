def test_exact_route_and_openapi_resource_contract(app):
    expected = {
        "/items": {"get", "post"},
        "/items/{item_id}": {"get", "put", "delete"},
        "/actions": {"get", "post"},
        "/actions/{action_id}": {"get", "put", "delete"},
        "/items/{item_id}/actions": {"get", "post"},
    }
    spec = app.test_client().get("/swagger/v1/swagger.json").json
    assert set(spec["paths"]) == set(expected)
    for path, methods in expected.items():
        operations = spec["paths"][path]
        assert set(operations) - {"parameters"} == methods
        for method in methods:
            response = operations[method]["responses"]
            assert "default" in response
            assert response["default"]["$ref"] == "#/components/responses/Problem"
        if "post" in methods:
            assert "Location" in operations["post"]["responses"]["201"]["headers"]
            assert "400" in operations["post"]["responses"]
    schemas = spec["components"]["schemas"]
    assert schemas["ItemResponse"]["properties"]["status"]["enum"] == ["active", "archived"]
    assert schemas["ActionResponse"]["properties"]["type"]["enum"] == ["create", "update", "delete"]
    assert "itemId" not in schemas["UpdateAction"]["properties"]
    assert "itemId" not in schemas["NestedAction"]["properties"]
    assert "itemId" in schemas["CreateAction"]["required"]
    assert schemas["CreateItem"]["additionalProperties"] is False
    assert schemas["CreateItem"]["properties"]["name"]["maxLength"] == 200
    assert schemas["CreateAction"]["properties"]["name"]["maxLength"] == 200
    assert schemas["ItemResponse"]["properties"]["id"]["format"] == "uuid"
    assert schemas["ActionResponse"]["properties"]["createdAt"]["format"] == "date-time"
    # A Blueprint registers one Rule per view; merge methods for the exact route surface.
    actual = {}
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith(("/items", "/actions")):
            actual.setdefault(rule.rule, set()).update(rule.methods - {"HEAD", "OPTIONS"})
    assert actual == {
        "/items": {"GET", "POST"},
        "/items/<uuid:item_id>": {"GET", "PUT", "DELETE"},
        "/actions": {"GET", "POST"},
        "/actions/<uuid:action_id>": {"GET", "PUT", "DELETE"},
        "/items/<uuid:item_id>/actions": {"GET", "POST"},
    }


def test_swagger_uses_local_assets_and_actual_spec(app):
    client = app.test_client()
    response = client.get("/swagger")
    assert response.status_code == 200
    assert "/swagger/v1/swagger.json" in response.text
    assert "/swagger-assets/" in response.text
    assert "https://" not in response.text
    for asset in ("swagger-ui.css", "swagger-ui-bundle.js", "swagger-ui-standalone-preset.js"):
        with client.get("/swagger-assets/" + asset) as asset_response:
            assert asset_response.status_code == 200
    assert client.get("/swagger-assets/../../requirements.txt").status_code == 404


def test_disabling_openapi_disables_ui_assets_and_spec(app_factory, explicit_config):
    client = app_factory({**explicit_config, "OPENAPI_ENABLED": "false"}).test_client()
    for path in ("/swagger", "/swagger/v1/swagger.json", "/swagger-assets/swagger-ui.css"):
        assert client.get(path).status_code == 404
