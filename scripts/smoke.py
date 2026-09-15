"""HTTP smoke assertions against an owned running stack, never Flask's test client."""

import json
import urllib.error
import urllib.request
from uuid import uuid4


def request(url, path, method="GET", payload=None, expected=200, raw=None):
    data = (
        raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
    )
    req = urllib.request.Request(url + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        response = urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        body = response.read().decode()
        assert response.status == expected, f"{method} {path}: {response.status}, wanted {expected}"
        headers = dict(response.headers)
        if expected >= 400 and path not in {"/health", "/ready"}:
            assert response.headers.get_content_type() == "application/problem+json"
            problem = json.loads(body)
            assert problem["status"] == expected
            assert {"type", "title", "detail", "status"} <= problem.keys()
            assert not any(
                secret in body.lower()
                for secret in (
                    "traceback",
                    "psycopg",
                    "postgresql://",
                    "postgresql+psycopg://",
                    "redis://",
                )
            )
        return (
            json.loads(body)
            if response.headers.get_content_type()
            in {"application/json", "application/problem+json"}
            else body
        ), headers


def redis(stack, *args):
    return stack.compose(
        "exec", "-T", "redis", "redis-cli", "--raw", *args, capture=True
    ).stdout.strip()


def sql(stack, query):
    database = "goalstats_template_py_" + stack.env
    return stack.compose(
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        "goalstats",
        "-d",
        database,
        "-At",
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        query,
        capture=True,
    ).stdout.strip()


def smoke_stack(stack, *, fault=False):
    url = stack.url
    assert request(url, "/health")[0] == "Healthy"
    assert request(url, "/ready")[0] == "Healthy"
    html, _ = request(url, "/swagger")
    assert "/swagger/v1/swagger.json" in html and "/swagger-assets/" in html
    assert "https://" not in html and "http://" not in html
    js, _ = request(url, "/swagger-assets/swagger-ui-bundle.js")
    assert "SwaggerUIBundle" in js
    spec, _ = request(url, "/swagger/v1/swagger.json")
    assert set(spec["paths"]) == {
        "/items",
        "/items/{item_id}",
        "/actions",
        "/actions/{action_id}",
        "/items/{item_id}/actions",
    }
    if fault:
        request(url, "/deliberately-missing-smoke-route")
    item, headers = request(url, "/items", "POST", {"name": "smoke"}, 201)
    item_path = "/items/" + item["id"]
    assert headers["Location"] == item_path
    prefix = f"goalstats-template-py:{stack.env}:v1"
    item_key = prefix + ":items:" + item["id"]
    try:
        assert request(url, item_path)[0] == item
        assert json.loads(redis(stack, "GET", item_key)) == item
        assert 0 < int(redis(stack, "TTL", item_key)) <= 300

        # INFO keyspace hit counters verify the HTTP read used Redis without corrupting data.
        def hits():
            lines = redis(stack, "INFO", "stats").splitlines()
            return int(next(s.split(":", 1)[1] for s in lines if s.startswith("keyspace_hits:")))

        before = hits()
        assert request(url, item_path)[0] == item
        assert hits() > before
        assert sql(stack, f"SELECT name FROM items WHERE id='{item['id']}'") == "smoke"
        item, _ = request(url, item_path, "PUT", {"name": "updated", "status": "archived"})
        assert redis(stack, "EXISTS", item_key) == "0"
        assert request(url, item_path)[0]["name"] == "updated"
        action, headers = request(
            url,
            "/actions",
            "POST",
            {
                "itemId": item["id"],
                "name": "action",
                "type": "create",
            },
            201,
        )
        action_path = "/actions/" + action["id"]
        assert headers["Location"] == action_path
        assert request(url, action_path)[0] == action
        action_key = prefix + ":actions:" + action["id"]
        assert redis(stack, "EXISTS", action_key) == "1"
        request(url, action_path, "PUT", {"name": "updated action", "type": "update"})
        assert redis(stack, "EXISTS", action_key) == "0"
        request(url, action_path)
        request(url, action_path, "DELETE", expected=204)
        assert redis(stack, "EXISTS", action_key) == "0"
        request(url, action_path, expected=404)
        nested, headers = request(
            url,
            item_path + "/actions",
            "POST",
            {
                "name": "nested",
                "type": "delete",
            },
            201,
        )
        assert headers["Location"] == "/actions/" + nested["id"]
        assert request(url, item_path + "/actions")[0] == [nested]
        assert nested in request(url, "/actions")[0]
        assert item in request(url, "/items")[0]
        request(url, "/actions/" + nested["id"])
        assert redis(stack, "EXISTS", prefix + ":actions:" + nested["id"]) == "1"
        request(url, item_path, "DELETE", expected=204)
        assert redis(stack, "EXISTS", item_key) == "0"
        # The child's old cache entry exists after DB cascade; HTTP must still return 404.
        assert redis(stack, "EXISTS", prefix + ":actions:" + nested["id"]) == "1"
        request(url, "/actions/" + nested["id"], expected=404)
        assert redis(stack, "EXISTS", prefix + ":actions:" + nested["id"]) == "0"
        assert sql(stack, f"SELECT count(*) FROM actions WHERE item_id='{item['id']}'") == "0"
        request(url, item_path, expected=404)
        request(url, "/items/" + str(uuid4()), expected=404)
        request(url, "/actions/" + str(uuid4()), expected=404)
        request(url, "/items", "POST", {"name": " "}, 400)
        request(url, "/items", "POST", expected=400, raw=b"{bad json")
        request(url, "/items", "PATCH", expected=405)
    finally:
        # Idempotent cleanup of only the row created by this smoke run.
        exists = any(row["id"] == item["id"] for row in request(url, "/items")[0])
        request(url, item_path, "DELETE", expected=204 if exists else 404)
    print(f"{stack.env.upper()} HTTP smoke: PASS", flush=True)
