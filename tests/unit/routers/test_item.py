from datetime import UTC, datetime
from unittest.mock import create_autospec
from uuid import uuid4

from flask_openapi3.openapi import OpenAPI

from exceptions.handlers import register_error_handlers, request_validation
from routers.item import create_items_blueprint
from schemas.item.request import ItemCreateRequest, ItemUpdateRequest
from schemas.item.response import ItemResponse
from services.item import ItemService


def test_item_router_uses_only_its_explicit_service():
    service = create_autospec(ItemService, instance=True, spec_set=True)
    result = ItemResponse(
        id=uuid4(),
        name="Item",
        status="active",
        createdAt=datetime.now(UTC),
        updatedAt=datetime.now(UTC),
    )
    for method in (service.create, service.get, service.update):
        method.return_value = result
    service.list.return_value = [result]
    app = OpenAPI(__name__, doc_ui=False, validation_error_callback=request_validation)
    app.register_api(create_items_blueprint(service))
    register_error_handlers(app)
    assert not any(key.startswith("goalstats_") for key in app.extensions)
    client = app.test_client()
    path = f"/items/{result.id}"
    expected = result.model_dump(mode="json", by_alias=True)

    response = client.post("/items", json={"name": "Item"})
    assert response.status_code == 201
    assert response.headers["Location"] == path
    assert response.json == expected
    service.create.assert_called_once_with(ItemCreateRequest(name="Item"))
    assert client.get(path).json == expected
    service.get.assert_called_once_with(result.id)
    assert client.get("/items").json == [expected]
    service.list.assert_called_once_with()
    assert client.put(path, json={"name": "Item", "status": "active"}).json == expected
    service.update.assert_called_once_with(
        result.id, ItemUpdateRequest(name="Item", status="active")
    )
    response = client.delete(path)
    assert response.status_code == 204 and response.data == b""
    service.delete.assert_called_once_with(result.id)

    assert client.post("/items", json={"name": " "}).status_code == 400
    assert service.create.call_count == 1
