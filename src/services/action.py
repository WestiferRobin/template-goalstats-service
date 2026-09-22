from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from exceptions.action import ActionNotFound
from exceptions.item import ItemNotFound
from infra.caches.action import ActionCache
from infra.repositories.action import ActionRepository
from infra.repositories.item import ItemRepository
from infra.resources.db import Database
from models.action import Action
from schemas.action.base import ActionPathSchema
from schemas.action.request import ActionCreateRequest, ActionWriteRequest
from schemas.action.response import ActionResponse
from schemas.item.base import ItemPathSchema


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

    def list(self, item_id: UUID | None = None) -> list[ActionResponse]:
        if item_id is not None:
            item_id = ItemPathSchema(item_id=item_id).item_id
        with self.database.transaction() as session:
            if item_id is not None and self.parents(session).get_by_id(item_id) is None:
                raise ItemNotFound()
            return [
                ActionResponse.model_validate(a, by_name=True, by_alias=False)
                for a in self.repository(session).list(item_id)
            ]

    def get(self, action_id: UUID) -> ActionResponse:
        action_id = ActionPathSchema(action_id=action_id).action_id
        cached = self.cache.get(action_id)
        with self.database.transaction() as session:
            repo = self.repository(session)
            if cached is not None:
                present = repo.exists(action_id)
                result = cached if present else None
            else:
                action = repo.get_by_id(action_id)
                result = (
                    ActionResponse.model_validate(action, by_name=True, by_alias=False)
                    if action is not None
                    else None
                )
        if result is None:
            if cached is not None:
                self.cache.delete(action_id)
            raise ActionNotFound()
        if cached is None:
            self.cache.set(result)
        return result

    def create(self, command: ActionCreateRequest) -> ActionResponse:
        item_id = command.item_id
        with self.database.transaction() as session:
            # Serialize with parent deletion; PostgreSQL still enforces the FK.
            if self.parents(session).get_by_id(item_id, for_update=True) is None:
                raise ItemNotFound()
            action = Action(item_id=item_id, name=command.name, action_type=command.action_type)
            self.repository(session).add(action)
            result = ActionResponse.model_validate(action, by_name=True, by_alias=False)
        return result

    def update(self, action_id: UUID, command: ActionWriteRequest) -> ActionResponse:
        action_id = ActionPathSchema(action_id=action_id).action_id
        with self.database.transaction() as session:
            repo = self.repository(session)
            action = repo.get_by_id(action_id, for_update=True)
            if action is None:
                raise ActionNotFound()
            action.name, action.action_type, action.updated_at = (
                command.name,
                command.action_type,
                datetime.now(UTC),
            )
            repo.flush()
            result = ActionResponse.model_validate(action, by_name=True, by_alias=False)
        self.cache.delete(action_id)
        return result

    def delete(self, action_id: UUID) -> None:
        action_id = ActionPathSchema(action_id=action_id).action_id
        with self.database.transaction() as session:
            repo = self.repository(session)
            action = repo.get_by_id(action_id, for_update=True)
            if action is None:
                raise ActionNotFound()
            repo.delete(action)
        self.cache.delete(action_id)
