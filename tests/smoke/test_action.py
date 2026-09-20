from uuid import uuid4

import pytest

pytestmark = pytest.mark.smoke


def test_action_crud_nested_cascade_and_cache(smoke_client, smoke_item):
    client, item = smoke_client, smoke_item
    item_path = "/items/" + item["id"]
    action, headers = client.request(
        "/actions",
        "POST",
        {
            "itemId": item["id"],
            "name": "action",
            "type": "create",
        },
        201,
    )
    path = "/actions/" + action["id"]
    key = client.prefix + ":actions:" + action["id"]
    assert headers["Location"] == path
    assert client.request(path)[0] == action
    assert client.redis.exists(key) == 1
    updated, _ = client.request(path, "PUT", {"name": "updated action", "type": "update"})
    assert client.redis.exists(key) == 0
    assert client.request(path)[0] == updated
    client.request(path, "DELETE", expected=204)
    assert client.redis.exists(key) == 0
    client.request(path, expected=404)
    nested, headers = client.request(
        item_path + "/actions",
        "POST",
        {
            "name": "nested",
            "type": "delete",
        },
        201,
    )
    assert headers["Location"] == "/actions/" + nested["id"]
    assert client.request(item_path + "/actions")[0] == [nested]
    assert nested in client.request("/actions")[0]
    child_path = "/actions/" + nested["id"]
    child_key = client.prefix + ":actions:" + nested["id"]
    assert client.request(child_path)[0] == nested
    assert client.redis.exists(child_key) == 1
    client.request(item_path, "DELETE", expected=204)
    assert client.redis.exists(child_key) == 1
    client.request(child_path, expected=404)
    assert client.redis.exists(child_key) == 0
    assert client.scalar("SELECT count(*) FROM actions WHERE item_id=%s", (item["id"],)) == 0
    client.request("/actions/" + str(uuid4()), expected=404)
