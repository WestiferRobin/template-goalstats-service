from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from enums.action import ActionType
from enums.item import ItemStatus
from exceptions.action import ActionNotFound
from exceptions.item import ItemNotFound
from infra.caches.action import ActionCache
from infra.repositories.action import ActionRepository
from infra.repositories.item import ItemRepository
from schemas.action.request import ActionCreateRequest, ActionWriteRequest
from schemas.action.response import ActionResponse
from schemas.item.request import ItemCreateRequest, ItemUpdateRequest
from schemas.item.response import ItemResponse
from services.action import ActionService


def test_cache_miss_fills_after_transaction(graph):
    result = graph.service.get(graph.row.id)
    assert result.id == graph.row.id
    assert graph.events == ["begin", "commit", "fill"]


def test_cache_hit_decisions(graph):
    cached = (ItemResponse if graph.kind == "item" else ActionResponse).model_validate(
        graph.row, by_name=True, by_alias=False
    )
    graph.cache.get.return_value = cached
    assert graph.service.get(graph.row.id) == cached
    assert graph.events == ([] if graph.kind == "item" else ["begin", "commit"])
    graph.repo.get_by_id.assert_not_called()
    graph.cache.set.assert_not_called()


def test_lists_are_uncached_and_creation_does_not_fill(graph):
    assert len(graph.service.list()) == 1
    result = (
        graph.service.create(ItemCreateRequest(name="new"))
        if graph.kind == "item"
        else graph.service.create(
            ActionCreateRequest(itemId=graph.row.item_id, name="new", type=ActionType.CREATE)
        )
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
            graph.row.id,
            ItemUpdateRequest(name="new", status=ItemStatus.ARCHIVED)
            if graph.kind == "item"
            else ActionWriteRequest(name="new", type=ActionType.UPDATE),
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
            graph.service.create(
                ItemCreateRequest(name="new")
            ) if graph.kind == "item" else graph.service.create(
                ActionCreateRequest(itemId=graph.row.item_id, name="new", type=ActionType.CREATE)
            )
        elif operation == "update":
            graph.service.update(
                graph.row.id,
                ItemUpdateRequest(name="new", status=ItemStatus.ACTIVE)
                if graph.kind == "item"
                else ActionWriteRequest(name="new", type=ActionType.UPDATE),
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
            graph.row.id,
            ItemUpdateRequest(name="valid", status=ItemStatus.ACTIVE)
            if graph.kind == "item"
            else ActionWriteRequest(name="valid", type=ActionType.UPDATE),
        )
    with pytest.raises(ValidationError):
        graph.service.get(UUID(int=0))
    with pytest.raises(ValidationError):
        ItemUpdateRequest(
            name=" ", status="invalid"
        ) if graph.kind == "item" else ActionWriteRequest(name=" ", type="invalid")
    with pytest.raises(ValidationError):
        ItemUpdateRequest(
            name="valid", status="invalid"
        ) if graph.kind == "item" else ActionWriteRequest(name="valid", type="invalid")


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
        service.create(ActionCreateRequest(itemId=uuid4(), name="x", type=ActionType.CREATE))
    with pytest.raises(ItemNotFound):
        service.list(uuid4())
    repo.add.assert_not_called()
    repo.exists.return_value = False
    identity = uuid4()
    cache.get.return_value = Mock(id=identity)
    with pytest.raises(ActionNotFound):
        service.get(identity)
    cache.delete.assert_called_once_with(identity)


def test_invalid_database_output_rolls_back_without_cache_fill(graph):
    graph.row.name = " "
    with pytest.raises(ValidationError):
        graph.service.get(graph.row.id)
    assert graph.events == ["begin", "rollback"]
    graph.cache.set.assert_not_called()


@pytest.mark.parametrize("kind", ["item", "action"])
@pytest.mark.parametrize("fail_one", [False, True])
def test_shared_service_overlapping_operations_are_isolated(kind, fail_one):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, Lock

    from flask import has_app_context

    from models.action import Action
    from models.item import Item
    from services.item import ItemService

    barrier, lock = Barrier(2, timeout=10), Lock()
    sessions, repositories, outcomes, invalidated = [], [], {}, []
    now = datetime.now(UTC)
    identities = (uuid4(), uuid4())

    class Operation:
        identity = None
        closed = False

    class DatabaseFake:
        @contextmanager
        def transaction(self):
            session = Operation()
            with lock:
                sessions.append(session)
            try:
                yield session
                if fail_one and session.identity == identities[0]:
                    raise RuntimeError("isolated commit failure")
                with lock:
                    outcomes[session.identity] = "commit"
            except BaseException:
                with lock:
                    outcomes[session.identity] = "rollback"
                raise
            finally:
                session.closed = True

    class RepositoryFake:
        def __init__(self, session):
            self.session = session
            with lock:
                repositories.append(self)

        def get_by_id(self, identity, *, for_update=False):
            assert for_update
            assert not has_app_context()
            self.session.identity = identity
            barrier.wait()
            values = dict(id=identity, name="old", created_at=now, updated_at=now)
            return (
                Item(**values, status=ItemStatus.ACTIVE)
                if kind == "item"
                else Action(**values, item_id=uuid4(), action_type=ActionType.CREATE)
            )

        def flush(self):
            assert not self.session.closed

    class CacheFake:
        def delete(self, identity):
            with lock:
                assert outcomes[identity] == "commit"
                assert next(s for s in sessions if s.identity == identity).closed
                invalidated.append(identity)

    database, cache = DatabaseFake(), CacheFake()
    service = (ItemService if kind == "item" else ActionService)(database, cache, RepositoryFake)
    original_attributes = vars(service).copy()

    def update(index):
        command = (
            ItemUpdateRequest(name=f"operation-{index}", status=ItemStatus.ARCHIVED)
            if kind == "item"
            else ActionWriteRequest(name=f"operation-{index}", type=ActionType.UPDATE)
        )
        return service.update(identities[index], command)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(update, index) for index in range(2)]
        for index, future in enumerate(futures):
            if fail_one and index == 0:
                with pytest.raises(RuntimeError, match="isolated commit failure"):
                    future.result(timeout=15)
            else:
                result = future.result(timeout=15)
                assert result.id == identities[index]
                assert result.name == f"operation-{index}"
    assert len(sessions) == len(repositories) == 2
    assert sessions[0] is not sessions[1]
    assert repositories[0] is not repositories[1]
    assert {id(repo.session) for repo in repositories} == {id(s) for s in sessions}
    assert all(session.closed for session in sessions)
    assert outcomes == {
        identities[0]: "rollback" if fail_one else "commit",
        identities[1]: "commit",
    }
    assert set(invalidated) == set(identities[1:] if fail_one else identities)
    assert vars(service) == original_attributes
