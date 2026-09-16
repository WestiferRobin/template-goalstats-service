from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from enums.action import ActionType
from exceptions.base import ActionNotFound, ItemNotFound, RequestValidationError
from infra.caches.action import ActionCache
from infra.repositories.action import ActionRepository
from infra.repositories.item import ItemRepository
from infra.resources.db import Database
from models import Action
from schemas.action.base import ActionResult
from services.item.validation import require_id, require_name


class ActionService:
    def __init__(
        self,
        database: Database,
        cache: ActionCache,
        repository: Callable[[Session], ActionRepository] = ActionRepository,
        parents: Callable[[Session], ItemRepository] = ItemRepository,
    ) -> None:
        self.database, self.cache = database, cache
        self.repository, self.parents = repository, parents

    def list(self, item_id: UUID | None = None) -> list[ActionResult]:
        if item_id is not None:
            require_id(item_id)
        with self.database.transaction() as session:
            if item_id is not None and self.parents(session).get_by_id(item_id) is None:
                raise ItemNotFound()
            return [ActionResult.from_model(a) for a in self.repository(session).list(item_id)]

    def get(self, action_id: UUID) -> ActionResult:
        require_id(action_id)
        cached = self.cache.get(action_id)
        with self.database.transaction() as session:
            repo = self.repository(session)
            if cached is not None:
                present = repo.exists(action_id)
                result = cached if present else None
            else:
                action = repo.get_by_id(action_id)
                result = ActionResult.from_model(action) if action is not None else None
        if result is None:
            if cached is not None:
                self.cache.delete(action_id)
            raise ActionNotFound()
        if cached is None:
            self.cache.set(result)
        return result

    def create(self, item_id: UUID, name: str, action_type: ActionType) -> ActionResult:
        require_id(item_id)
        require_name(name)
        action_type = self._type(action_type)
        with self.database.transaction() as session:
            # Serialize with parent deletion; PostgreSQL still enforces the FK.
            if self.parents(session).get_by_id(item_id, for_update=True) is None:
                raise ItemNotFound()
            action = Action(item_id=item_id, name=name, action_type=action_type)
            self.repository(session).add(action)
            result = ActionResult.from_model(action)
        return result

    def update(self, action_id: UUID, name: str, action_type: ActionType) -> ActionResult:
        require_id(action_id)
        require_name(name)
        action_type = self._type(action_type)
        with self.database.transaction() as session:
            repo = self.repository(session)
            action = repo.get_by_id(action_id, for_update=True)
            if action is None:
                raise ActionNotFound()
            action.name, action.action_type, action.updated_at = (
                name,
                action_type,
                datetime.now(UTC),
            )
            repo.flush()
            result = ActionResult.from_model(action)
        self.cache.delete(action_id)
        return result

    def delete(self, action_id: UUID) -> None:
        require_id(action_id)
        with self.database.transaction() as session:
            repo = self.repository(session)
            action = repo.get_by_id(action_id, for_update=True)
            if action is None:
                raise ActionNotFound()
            repo.delete(action)
        self.cache.delete(action_id)

    @staticmethod
    def _type(value: ActionType) -> ActionType:
        try:
            return ActionType(value)
        except (ValueError, TypeError):
            raise RequestValidationError() from None
