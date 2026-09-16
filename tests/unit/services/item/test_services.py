from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from enums.action import ActionType
from enums.item import ItemStatus
from exceptions.base import ActionNotFound, ItemNotFound, RequestValidationError
from infra.caches.action import ActionCache
from infra.repositories.action import ActionRepository
from infra.repositories.item import ItemRepository
from schemas.action.base import ActionResult
from schemas.item.base import ItemResult
from services.item.action import ActionService


def test_cache_miss_fills_after_transaction(graph):
    result = graph.service.get(graph.row.id)
    assert result.id == graph.row.id
    assert graph.events == ["begin", "commit", "fill"]


def test_cache_hit_decisions(graph):
    cached = (ItemResult if graph.kind == "item" else ActionResult).from_model(graph.row)
    graph.cache.get.return_value = cached
    assert graph.service.get(graph.row.id) == cached
    assert graph.events == ([] if graph.kind == "item" else ["begin", "commit"])
    graph.repo.get_by_id.assert_not_called()
    graph.cache.set.assert_not_called()


def test_lists_are_uncached_and_creation_does_not_fill(graph):
    assert len(graph.service.list()) == 1
    result = (
        graph.service.create("new")
        if graph.kind == "item"
        else graph.service.create(graph.row.item_id, "new", ActionType.CREATE)
    )
    assert result.name == "new"
    graph.cache.get.assert_not_called()
    graph.cache.set.assert_not_called()
    graph.cache.delete.assert_not_called()


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_successful_mutation_invalidates_after_commit(graph, operation):
    if operation == "delete":
        graph.service.delete(graph.row.id)
    else:
        result = graph.service.update(
            graph.row.id, "new", ItemStatus.ARCHIVED if graph.kind == "item" else ActionType.UPDATE
        )
        assert result.created_at == datetime(2026, 1, 1, tzinfo=UTC)
        assert result.updated_at > result.created_at
    assert graph.events == ["begin", "commit", "invalidate"]
    graph.repo.get_by_id.assert_called_once_with(graph.row.id, for_update=True)


@pytest.mark.parametrize("failure", ["flush", "commit"])
@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_failed_mutation_never_mutates_cache(graph, failure, operation):
    graph.state["fail_commit"] = failure == "commit"
    if failure == "flush":
        for method in [graph.repo.add, graph.repo.flush, graph.repo.delete]:
            method.side_effect = RuntimeError("provider failed")
    with pytest.raises(RuntimeError):
        if operation == "create":
            graph.service.create("new") if graph.kind == "item" else graph.service.create(
                graph.row.item_id, "new", ActionType.CREATE
            )
        elif operation == "update":
            graph.service.update(
                graph.row.id,
                "new",
                ItemStatus.ACTIVE if graph.kind == "item" else ActionType.UPDATE,
            )
        else:
            graph.service.delete(graph.row.id)
    assert graph.events == ["begin", "rollback"]
    graph.cache.set.assert_not_called()
    graph.cache.delete.assert_not_called()


def test_missing_resource_and_invalid_direct_calls(graph):
    graph.repo.get_by_id.return_value = None
    error = ItemNotFound if graph.kind == "item" else ActionNotFound
    for method in [graph.service.get, graph.service.delete]:
        with pytest.raises(error):
            method(graph.row.id)
    with pytest.raises(error):
        graph.service.update(
            graph.row.id, "valid", ItemStatus.ACTIVE if graph.kind == "item" else ActionType.UPDATE
        )
    with pytest.raises(RequestValidationError):
        graph.service.get(UUID(int=0))
    with pytest.raises(RequestValidationError):
        graph.service.update(graph.row.id, " ", "invalid")
    with pytest.raises(RequestValidationError):
        graph.service.update(graph.row.id, "valid", "invalid")


def test_action_parent_missing_and_stale_child_guard():
    cache, repo, parents, db = (
        Mock(spec=ActionCache),
        Mock(spec=ActionRepository),
        Mock(spec=ItemRepository),
        Mock(),
    )

    @contextmanager
    def transaction():
        yield None

    db.transaction.side_effect = transaction
    service = ActionService(db, cache, lambda session: repo, lambda session: parents)
    parents.get_by_id.return_value = None
    with pytest.raises(ItemNotFound):
        service.create(uuid4(), "x", ActionType.CREATE)
    with pytest.raises(ItemNotFound):
        service.list(uuid4())
    repo.add.assert_not_called()
    repo.exists.return_value = False
    identity = uuid4()
    cache.get.return_value = Mock(id=identity)
    with pytest.raises(ActionNotFound):
        service.get(identity)
    cache.delete.assert_called_once_with(identity)
