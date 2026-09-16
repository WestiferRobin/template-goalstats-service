from uuid import UUID

from marshmallow import ValidationError

from infra.resources.redis import RedisCache
from schemas.action.base import ActionResult
from schemas.action.response import ActionResponseSchema


class ActionCache:
    def __init__(self, cache: RedisCache, prefix: str, ttl: int) -> None:
        self.cache, self.prefix, self.ttl = cache, prefix, ttl
        self.schema = ActionResponseSchema()

    def key(self, resource_id: UUID) -> str:
        return f"{self.prefix}:actions:{resource_id}"

    def get(self, resource_id: UUID) -> ActionResult | None:
        payload = self.cache.get(self.key(resource_id))
        if payload is None:
            return None
        try:
            result = ActionResult(**self.schema.load(payload))
            if result.id == resource_id:
                return result
        except (ValidationError, TypeError, ValueError):
            pass
        self.delete(resource_id)
        return None

    def set(self, result: ActionResult) -> None:
        self.cache.set(self.key(result.id), self.schema.dump(result), self.ttl)

    def delete(self, resource_id: UUID) -> None:
        self.cache.delete(self.key(resource_id))
