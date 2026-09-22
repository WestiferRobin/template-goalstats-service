from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import DataError, IntegrityError

from enums.item import ItemStatus
from exceptions.item import ItemNotFound
from infra.repositories.action import ActionRepository
from infra.repositories.item import ItemRepository
from models.action import Action
from models.item import Item
from schemas.item.request import ItemUpdateRequest
from services.item import ItemService

pytestmark = pytest.mark.postgres


def test_repositories_flush_without_committing_and_lists_are_deterministic(postgres_app):
    db = postgres_app.extensions["goalstats_database"]
    with db.sessions() as session:
        ItemRepository(session).add(Item(name="rollback", status=ItemStatus.ACTIVE))
    with db.transaction() as session:
        assert ItemRepository(session).list() == []
        stamp = datetime(2026, 1, 1, tzinfo=UTC)
        ids = sorted([uuid4(), uuid4()])
        for identity in reversed(ids):
            ItemRepository(session).add(
                Item(id=identity, name="same", status=ItemStatus.ACTIVE, created_at=stamp)
            )
        assert [item.id for item in ItemRepository(session).list()] == ids
        assert ActionRepository(session).list() == []


@pytest.mark.parametrize(
    "name,value,expected",
    [
        ("", "active", "23514"),
        (" ", "active", "23514"),
        (None, "active", "23502"),
        ("x" * 201, "active", "22001"),
        ("ok", "bad", "23514"),
    ],
)
def test_database_item_constraints(postgres_app, name, value, expected):
    db = postgres_app.extensions["goalstats_database"]
    with pytest.raises((IntegrityError, DataError)) as error:
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO items (id,name,status,created_at,updated_at) "
                    "VALUES (:id,:name,:value,now(),now())"
                ),
                {"id": uuid4(), "name": name, "value": value},
            )
    assert error.value.orig.sqlstate == expected


def test_action_fk_check_constraints_and_schema_metadata(postgres_app):
    db = postgres_app.extensions["goalstats_database"]
    with pytest.raises(IntegrityError) as error:
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO actions (id,item_id,name,action_type,created_at,updated_at) "
                    "VALUES (:id,:parent,'x','create',now(),now())"
                ),
                {"id": uuid4(), "parent": uuid4()},
            )
    assert error.value.orig.sqlstate == "23503"
    client = postgres_app.test_client()
    parent = client.post("/items", json={"name": "parent"}).json["id"]
    for name, kind in [("", "create"), ("x", "bad")]:
        with pytest.raises(IntegrityError):
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO actions (id,item_id,name,action_type,created_at,updated_at) "
                        "VALUES (:id,:parent,:name,:kind,now(),now())"
                    ),
                    {"id": uuid4(), "parent": parent, "name": name, "kind": kind},
                )
    schema = inspect(db.engine)
    assert schema.get_foreign_keys("actions")[0]["options"]["ondelete"] == "CASCADE"
    assert any(index["column_names"] == ["item_id"] for index in schema.get_indexes("actions"))
    assert all(
        column["type"].timezone
        for column in schema.get_columns("items")
        if column["name"] in {"created_at", "updated_at"}
    )


def test_cascade_and_duplicate_primary_key(postgres_app):
    client = postgres_app.test_client()
    parent = client.post("/items", json={"name": "parent"}).json["id"]
    action = client.post(
        "/actions", json={"itemId": parent, "name": "action", "type": "create"}
    ).json["id"]
    db = postgres_app.extensions["goalstats_database"]
    with pytest.raises(IntegrityError) as error:
        with db.engine.begin() as connection:
            connection.execute(
                text("INSERT INTO items SELECT * FROM items WHERE id=:id"), {"id": parent}
            )
    assert error.value.orig.sqlstate == "23505"
    assert client.delete("/items/" + parent).status_code == 204
    with db.transaction() as session:
        assert session.scalar(select(Action)) is None
    assert client.get("/actions/" + action).status_code == 404


def test_concurrent_update_delete_has_no_unhandled_stale_row(postgres_app):
    client = postgres_app.test_client()
    identity = client.post("/items", json={"name": "race"}).json["id"]
    from uuid import UUID

    identity = UUID(identity)
    db, cache = (
        postgres_app.extensions["goalstats_database"],
        postgres_app.extensions["goalstats_item_cache"],
    )
    barrier = Barrier(2)

    def update():
        barrier.wait(timeout=5)
        try:
            ItemService(db, cache).update(
                identity, ItemUpdateRequest(name="updated", status=ItemStatus.ARCHIVED)
            )
            return "updated"
        except ItemNotFound:
            return "missing"

    def delete():
        barrier.wait(timeout=5)
        ItemService(db, cache).delete(identity)

    with ThreadPoolExecutor(max_workers=2) as executor:
        a, b = executor.submit(update), executor.submit(delete)
        assert a.result(timeout=10) in {"updated", "missing"}
        b.result(timeout=10)
    assert client.get("/items/" + str(identity)).status_code == 404
