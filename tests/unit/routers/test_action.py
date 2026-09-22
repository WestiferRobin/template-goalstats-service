from datetime import UTC, datetime
from unittest.mock import create_autospec
from uuid import uuid4

from flask_openapi3.openapi import OpenAPI

from exceptions.handlers import register_error_handlers, request_validation
from routers.action import create_actions_blueprint
from schemas.action.request import ActionCreateRequest, ActionWriteRequest
from schemas.action.response import ActionResponse
from services.action import ActionService


def test_action_router_uses_only_its_explicit_service_including_nested_operations():
    service = create_autospec(ActionService, instance=True, spec_set=True)
    parent = uuid4()
    result = ActionResponse(
        id=uuid4(),
        itemId=parent,
        name="Action",
        type="create",
        createdAt=datetime.now(UTC),
        updatedAt=datetime.now(UTC),
    )
    for method in (service.create, service.get, service.update):
        method.return_value = result
    service.list.return_value = [result]
    app = OpenAPI(__name__, doc_ui=False, validation_error_callback=request_validation)
    app.register_api(create_actions_blueprint(service))
    register_error_handlers(app)
    assert not any(key.startswith("goalstats_") for key in app.extensions)
    client = app.test_client()
    path, nested = f"/actions/{result.id}", f"/items/{parent}/actions"
    expected = result.model_dump(mode="json", by_alias=True)
    body = {"name": "Action", "type": "create"}
    command = ActionCreateRequest(**body, itemId=parent)

    for target, payload in (("/actions", {**body, "itemId": str(parent)}), (nested, body)):
        response = client.post(target, json=payload)
        assert response.status_code == 201
        assert response.headers["Location"] == path
        assert response.json == expected
        service.create.assert_called_with(command)
    assert service.create.call_count == 2
    assert client.get(path).json == expected
    service.get.assert_called_once_with(result.id)
    assert client.get("/actions").json == [expected]
    service.list.assert_called_with()
    assert client.get(nested).json == [expected]
    service.list.assert_called_with(parent)
    assert client.put(path, json=body).json == expected
    service.update.assert_called_once_with(result.id, ActionWriteRequest(**body))
    response = client.delete(path)
    assert response.status_code == 204 and response.data == b""
    service.delete.assert_called_once_with(result.id)
    assert client.post(nested, json={**body, "itemId": str(uuid4())}).status_code == 400
    assert service.create.call_count == 2
