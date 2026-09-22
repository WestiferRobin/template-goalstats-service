from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from enums.item import ItemStatus
from exceptions.item import ItemNotFound
from infra.caches.item import ItemCache
from infra.repositories.item import ItemRepository
from infra.resources.db import Database
from models.item import Item
from schemas.item.base import ItemPathSchema
from schemas.item.request import ItemCreateRequest, ItemUpdateRequest
from schemas.item.response import ItemResponse


class ItemService:
    def __init__(
        self,
        database: Database,
        cache: ItemCache,
        repository: Callable[[Session], ItemRepository] = ItemRepository,
    ) -> None:
        self.database, self.cache, self.repository = database, cache, repository

    def list(self) -> list[ItemResponse]:
        with self.database.transaction() as session:
            return [
                ItemResponse.model_validate(item, by_name=True, by_alias=False)
                for item in self.repository(session).list()
            ]

    def get(self, item_id: UUID) -> ItemResponse:
        item_id = ItemPathSchema(item_id=item_id).item_id
        cached = self.cache.get(item_id)
        if cached is not None:
            return cached
        with self.database.transaction() as session:
            item = self.repository(session).get_by_id(item_id)
            if item is None:
                raise ItemNotFound()
            result = ItemResponse.model_validate(item, by_name=True, by_alias=False)
        self.cache.set(result)
        return result

    def create(self, command: ItemCreateRequest) -> ItemResponse:
        with self.database.transaction() as session:
            item = Item(name=command.name, status=ItemStatus.ACTIVE)
            self.repository(session).add(item)
            result = ItemResponse.model_validate(item, by_name=True, by_alias=False)
        return result

    def update(self, item_id: UUID, command: ItemUpdateRequest) -> ItemResponse:
        item_id = ItemPathSchema(item_id=item_id).item_id
        with self.database.transaction() as session:
            repo = self.repository(session)
            item = repo.get_by_id(item_id, for_update=True)
            if item is None:
                raise ItemNotFound()
            item.name, item.status, item.updated_at = (
                command.name,
                command.status,
                datetime.now(UTC),
            )
            repo.flush()
            result = ItemResponse.model_validate(item, by_name=True, by_alias=False)
        self.cache.delete(item_id)
        return result

    def delete(self, item_id: UUID) -> None:
        item_id = ItemPathSchema(item_id=item_id).item_id
        with self.database.transaction() as session:
            repo = self.repository(session)
            item = repo.get_by_id(item_id, for_update=True)
            if item is None:
                raise ItemNotFound()
            repo.delete(item)
        self.cache.delete(item_id)
