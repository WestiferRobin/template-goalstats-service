from datetime import datetime
from uuid import UUID, uuid4

import pytest

pytestmark = pytest.mark.postgres


def problem(response, status):
    assert response.status_code == status
    assert response.mimetype == "application/problem+json"
    assert response.json["status"] == status


def test_item_crud_serialization_and_order(postgres_app):
    client = postgres_app.test_client()
    assert client.get("/items").json == []
    created = client.post("/items", json={"name": "first"})
    assert created.status_code == 201
    item = created.json
    assert set(item) == {"id", "name", "status", "createdAt", "updatedAt"}
    assert str(UUID(item["id"])) == item["id"]
    assert item["status"] == "active"
    assert datetime.fromisoformat(item["createdAt"]).utcoffset().total_seconds() == 0
    location = created.headers["Location"]
    assert location == "/items/" + item["id"]
    assert client.get(location).json == item
    second = client.post("/items", json={"name": "first"}).json
    assert second["id"] != item["id"]  # names are deliberately not unique
    assert [row["id"] for row in client.get("/items").json] == [item["id"], second["id"]]
    updated = client.put(location, json={"name": "first", "status": "archived"})
    assert updated.status_code == 200
    assert updated.json["createdAt"] == item["createdAt"]
    assert updated.json["updatedAt"] > item["updatedAt"]
    assert updated.json["status"] == "archived"
    assert client.delete(location).status_code == 204
    assert client.delete(location).data != b""  # second delete is a documented missing resource
    problem(client.get(location), 404)
    problem(client.put(location, json={"name": "x", "status": "active"}), 404)


def test_action_crud_top_level_nested_and_immutable_parent(postgres_app):
    client = postgres_app.test_client()
    first = client.post("/items", json={"name": "first"}).json
    second = client.post("/items", json={"name": "second"}).json
    nested = "/items/" + first["id"] + "/actions"
    assert client.get(nested).json == []
    created = client.post(nested, json={"name": "act", "type": "create"})
    assert created.status_code == 201
    action = created.json
    assert set(action) == {"id", "itemId", "name", "type", "createdAt", "updatedAt"}
    assert action["itemId"] == first["id"]
    location = "/actions/" + action["id"]
    assert created.headers["Location"] == location
    assert client.get(location).json == action
    assert client.get(nested).json == [action]
    assert client.get("/items/" + second["id"] + "/actions").json == []
    top = client.post("/actions", json={"itemId": second["id"], "name": "top", "type": "delete"})
    assert top.status_code == 201
    assert top.headers["Location"] == "/actions/" + top.json["id"]
    assert len(client.get("/actions").json) == 2
    updated = client.put(location, json={"name": "updated", "type": "update"})
    assert updated.status_code == 200
    assert updated.json["itemId"] == first["id"]
    assert updated.json["createdAt"] == action["createdAt"]
    problem(client.put(location, json={"name": "x", "type": "create", "itemId": second["id"]}), 400)
    problem(client.post(nested, json={"name": "x", "type": "create", "itemId": second["id"]}), 400)
    response = client.delete(location)
    assert response.status_code == 204 and response.data == b""
    problem(client.get(location), 404)
    problem(client.delete(location), 404)
    problem(client.put(location, json={"name": "x", "type": "update"}), 404)


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("post", "/items", {}),
        ("post", "/items", {"name": " "}),
        ("post", "/items", {"name": "x" * 201}),
        ("post", "/items", {"name": None}),
        ("post", "/items", []),
        ("post", "/items", {"name": "x", "extra": 1}),
        ("post", "/actions", {"itemId": "bad", "name": "x", "type": "create"}),
        ("post", "/actions", {"itemId": str(uuid4()), "name": "x", "type": 0}),
    ],
)
def test_http_binding_validation(postgres_app, method, path, body):
    problem(getattr(postgres_app.test_client(), method)(path, json=body), 400)


def test_malformed_json_unsupported_methods_and_missing_parents(postgres_app):
    client = postgres_app.test_client()
    for path in ["/items", "/actions"]:
        problem(client.post(path, data="{", content_type="application/json"), 400)
        response = client.patch(path)
        problem(response, 405)
        assert "Allow" in response.headers
    missing = str(uuid4())
    problem(client.get("/items/" + missing), 404)
    problem(client.get("/items/" + missing + "/actions"), 404)
    problem(
        client.post("/items/" + missing + "/actions", json={"name": "x", "type": "create"}), 404
    )
    problem(client.post("/actions", json={"itemId": missing, "name": "x", "type": "create"}), 404)
    problem(client.get("/actions/not-a-uuid"), 404)


def test_body_guard_and_zero_uuid_preserve_errors(postgres_app):
    client = postgres_app.test_client()
    for path in ("/items", "/actions"):
        for body in ([], '{"name":"x"}'):
            response = client.post(path, json=body)
            problem(response, 400)
            assert response.json["detail"] == "The request could not be understood."
        problem(client.post(path, data='{"name":"x"}', content_type="text/plain"), 400)
    for path in ("/items/", "/actions/"):
        response = client.get(path + str(UUID(int=0)))
        problem(response, 400)
        assert response.json["detail"] == "The request contains invalid values."
    problem(
        client.post("/actions", json={"item_id": str(uuid4()), "name": "x", "type": "create"}), 400
    )
