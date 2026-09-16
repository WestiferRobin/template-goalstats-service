import json
from uuid import uuid4

import pytest

pytestmark = pytest.mark.smoke


def test_item_crud_persistence_and_cache(smoke_client, smoke_item):
    client, item = smoke_client, smoke_item
    path = "/items/" + item["id"]
    key = client.prefix + ":items:" + item["id"]
    assert client.request(path)[0] == item
    assert json.loads(client.redis.get(key)) == item
    assert 0 < client.redis.ttl(key) <= 300
    before = client.redis.info("stats")["keyspace_hits"]
    assert client.request(path)[0] == item
    assert client.redis.info("stats")["keyspace_hits"] > before
    assert client.scalar("SELECT name FROM items WHERE id=%s", (item["id"],)) == "smoke"
    updated, _ = client.request(path, "PUT", {"name": "updated", "status": "archived"})
    assert client.redis.exists(key) == 0
    assert client.request(path)[0] == updated
    assert updated in client.request("/items")[0]
    client.request(path, "DELETE", expected=204)
    assert client.redis.exists(key) == 0
    client.request(path, expected=404)
    client.request("/items/" + str(uuid4()), expected=404)


@pytest.mark.parametrize(
    "method,payload,raw,status",
    [
        ("POST", {"name": " "}, None, 400),
        ("POST", None, b"{bad json", 400),
        ("PATCH", None, None, 405),
    ],
)
def test_problem_details(smoke_client, method, payload, raw, status):
    problem, headers = smoke_client.request("/items", method, payload, status, raw)
    assert problem["status"] == status
    if status == 405:
        assert "GET" in headers["Allow"]
