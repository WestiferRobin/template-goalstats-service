from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from goalstats_template.enums.item import ItemStatus
from goalstats_template.exceptions.base import ItemNotFound, RequestValidationError
from goalstats_template.infra.caches.item import ItemCache
from goalstats_template.infra.repositories.item import ItemRepository
from goalstats_template.infra.resources.db import Database
from goalstats_template.models import Item
from goalstats_template.schemas.item.base import ItemResult
from goalstats_template.services.item.validation import require_id, require_name


class ItemService:
    def __init__(
        self,
        database: Database,
        cache: ItemCache,
        repository: Callable[[Session], ItemRepository] = ItemRepository,
    ) -> None:
        self.database, self.cache, self.repository = database, cache, repository

    def list(self) -> list[ItemResult]:
        with self.database.transaction() as session:
            return [ItemResult.from_model(item) for item in self.repository(session).list()]

    def get(self, item_id: UUID) -> ItemResult:
        require_id(item_id)
        cached = self.cache.get(item_id)
        if cached is not None:
            return cached
        with self.database.transaction() as session:
            item = self.repository(session).get_by_id(item_id)
            if item is None:
                raise ItemNotFound()
            result = ItemResult.from_model(item)
        self.cache.set(result)
        return result

    def create(self, name: str) -> ItemResult:
        require_name(name)
        with self.database.transaction() as session:
            item = Item(name=name, status=ItemStatus.ACTIVE)
            self.repository(session).add(item)
            result = ItemResult.from_model(item)
        return result

    def update(self, item_id: UUID, name: str, status: ItemStatus) -> ItemResult:
        require_id(item_id)
        require_name(name)
        try:
            status = ItemStatus(status)
        except (ValueError, TypeError):
            raise RequestValidationError() from None
        with self.database.transaction() as session:
            repo = self.repository(session)
            item = repo.get_by_id(item_id, for_update=True)
            if item is None:
                raise ItemNotFound()
            item.name, item.status, item.updated_at = name, status, datetime.now(UTC)
            repo.flush()
            result = ItemResult.from_model(item)
        self.cache.delete(item_id)
        return result

    def delete(self, item_id: UUID) -> None:
        require_id(item_id)
        with self.database.transaction() as session:
            repo = self.repository(session)
            item = repo.get_by_id(item_id, for_update=True)
            if item is None:
                raise ItemNotFound()
            repo.delete(item)
        self.cache.delete(item_id)
