from uuid import UUID

from pydantic import ValidationError

from infra.resources.redis import RedisCache
from schemas.item.response import ItemResponse


class ItemCache:
    def __init__(self, cache: RedisCache, prefix: str, ttl: int) -> None:
        self.cache, self.prefix, self.ttl = cache, prefix, ttl

    def key(self, resource_id: UUID) -> str:
        return f"{self.prefix}:items:{resource_id}"

    def get(self, resource_id: UUID) -> ItemResponse | None:
        payload = self.cache.get(self.key(resource_id))
        if payload is None:
            return None
        try:
            result = ItemResponse.model_validate(payload)
            if result.id == resource_id:
                return result
        except (ValidationError, TypeError, ValueError):
            pass
        self.delete(resource_id)
        return None

    def set(self, result: ItemResponse) -> None:
        self.cache.set(self.key(result.id), result.model_dump(mode="json", by_alias=True), self.ttl)

    def delete(self, resource_id: UUID) -> None:
        self.cache.delete(self.key(resource_id))
