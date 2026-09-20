from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from enums.action import ActionType
from enums.item import ItemStatus
from infra.caches.action import ActionCache
from infra.caches.item import ItemCache
from infra.repositories.action import ActionRepository
from infra.repositories.item import ItemRepository
from models.action import Action
from models.item import Item
from services.action import ActionService
from services.item import ItemService


@dataclass
class ServiceGraph:
    kind: str
    row: Item | Action
    repo: Mock
    parents: Mock
    cache: Mock
    service: ItemService | ActionService
    events: list[str]
    state: dict[str, bool]


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
    return ServiceGraph(kind, row, repo, parents, cache, service, events, state)
