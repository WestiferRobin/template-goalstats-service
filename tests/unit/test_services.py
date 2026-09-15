from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from goalstats_template.enums import ActionType, ItemStatus
from goalstats_template.errors import ActionNotFound, ItemNotFound, RequestValidationError
from goalstats_template.infrastructure.cache.actions import ActionCache
from goalstats_template.infrastructure.cache.items import ItemCache
from goalstats_template.infrastructure.database.repositories.actions import ActionRepository
from goalstats_template.infrastructure.database.repositories.items import ItemRepository
from goalstats_template.models import Action, Item
from goalstats_template.services.actions import ActionService
from goalstats_template.services.items import ItemService
from goalstats_template.services.results import ActionResult, ItemResult


@pytest.fixture(params=["item", "action"])
def graph(request):
    events = []
    now = datetime(2026, 1, 1, tzinfo=UTC)
    item = Item(id=uuid4(), name="old", status=ItemStatus.ACTIVE, created_at=now, updated_at=now)
    action = Action(
        id=uuid4(),
        item_id=item.id,
        name="old",
        action_type=ActionType.CREATE,
        created_at=now,
        updated_at=now,
    )
    kind = request.param
    row = item if kind == "item" else action
    repo = Mock(spec=ItemRepository if kind == "item" else ActionRepository)
    repo.get_by_id.return_value = row
    repo.list.return_value = [row]
    if kind == "action":
        repo.exists.return_value = True
    parents = Mock(spec=ItemRepository)
    parents.get_by_id.return_value = item
    cache = Mock(spec=ItemCache if kind == "item" else ActionCache)
    cache.get.return_value = None
    cache.delete.side_effect = lambda identity: events.append("invalidate")
    cache.set.side_effect = lambda result: events.append("fill")
    state = {"fail_commit": False}

    @contextmanager
    def transaction():
        events.append("begin")
        try:
            yield None
            if state["fail_commit"]:
                raise RuntimeError("commit failed")
            events.append("commit")
        except BaseException:
            events.append("rollback")
            raise

    database = Mock()
    database.transaction.side_effect = transaction

    def add(model):
        model.id, model.created_at, model.updated_at = uuid4(), now, now

    repo.add.side_effect = add
    service = (
        ItemService(database, cache, lambda session: repo)
        if kind == "item"
        else ActionService(database, cache, lambda session: repo, lambda session: parents)
    )
    return kind, row, repo, parents, cache, service, events, state


def test_cache_miss_fills_after_transaction(graph):
    kind, row, repo, parents, cache, service, events, state = graph
    result = service.get(row.id)
    assert result.id == row.id
    assert events == ["begin", "commit", "fill"]


def test_cache_hit_decisions(graph):
    kind, row, repo, parents, cache, service, events, state = graph
    cached = (ItemResult if kind == "item" else ActionResult).from_model(row)
    cache.get.return_value = cached
    assert service.get(row.id) == cached
    assert events == ([] if kind == "item" else ["begin", "commit"])
    repo.get_by_id.assert_not_called()
    cache.set.assert_not_called()


def test_lists_are_uncached_and_creation_does_not_fill(graph):
    kind, row, repo, parents, cache, service, events, state = graph
    assert len(service.list()) == 1
    result = (
        service.create("new")
        if kind == "item"
        else service.create(row.item_id, "new", ActionType.CREATE)
    )
    assert result.name == "new"
    cache.get.assert_not_called()
    cache.set.assert_not_called()
    cache.delete.assert_not_called()


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_successful_mutation_invalidates_after_commit(graph, operation):
    kind, row, repo, parents, cache, service, events, state = graph
    if operation == "delete":
        service.delete(row.id)
    else:
        result = service.update(
            row.id, "new", ItemStatus.ARCHIVED if kind == "item" else ActionType.UPDATE
        )
        assert result.created_at == datetime(2026, 1, 1, tzinfo=UTC)
        assert result.updated_at > result.created_at
    assert events == ["begin", "commit", "invalidate"]
    repo.get_by_id.assert_called_once_with(row.id, for_update=True)


@pytest.mark.parametrize("failure", ["flush", "commit"])
@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_failed_mutation_never_mutates_cache(graph, failure, operation):
    kind, row, repo, parents, cache, service, events, state = graph
    state["fail_commit"] = failure == "commit"
    if failure == "flush":
        for method in [repo.add, repo.flush, repo.delete]:
            method.side_effect = RuntimeError("provider failed")
    with pytest.raises(RuntimeError):
        if operation == "create":
            service.create("new") if kind == "item" else service.create(
                row.item_id, "new", ActionType.CREATE
            )
        elif operation == "update":
            service.update(
                row.id, "new", ItemStatus.ACTIVE if kind == "item" else ActionType.UPDATE
            )
        else:
            service.delete(row.id)
    assert events == ["begin", "rollback"]
    cache.set.assert_not_called()
    cache.delete.assert_not_called()


def test_missing_resource_and_invalid_direct_calls(graph):
    kind, row, repo, parents, cache, service, events, state = graph
    repo.get_by_id.return_value = None
    error = ItemNotFound if kind == "item" else ActionNotFound
    for method in [service.get, service.delete]:
        with pytest.raises(error):
            method(row.id)
    with pytest.raises(error):
        service.update(row.id, "valid", ItemStatus.ACTIVE if kind == "item" else ActionType.UPDATE)
    with pytest.raises(RequestValidationError):
        service.get(UUID(int=0))
    with pytest.raises(RequestValidationError):
        service.update(row.id, " ", "invalid")
    with pytest.raises(RequestValidationError):
        service.update(row.id, "valid", "invalid")


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
