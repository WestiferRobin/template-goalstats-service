from typing import Any
from uuid import UUID

from flask import Response, url_for

from composition import get_action_service, get_item_service
from routers import ApiBlueprint
from schemas.action.base import ActionResult
from schemas.action.request import NestedActionSchema
from schemas.action.response import ActionResponseSchema
from schemas.item.base import ItemResult
from schemas.item.request import CreateItemSchema, UpdateItemSchema
from schemas.item.response import ItemResponseSchema

LOCATION = {"Location": {"description": "Canonical resource URL", "schema": {"type": "string"}}}


def create_items_blueprint() -> ApiBlueprint:
    blueprint = ApiBlueprint("items", __name__, description="Item reference resources")

    @blueprint.get("/items")  # type: ignore[untyped-decorator]
    @blueprint.response(200, ItemResponseSchema(many=True))  # type: ignore[untyped-decorator]
    def list_all() -> list[ItemResult]:
        return get_item_service().list()

    @blueprint.post("/items")  # type: ignore[untyped-decorator]
    @blueprint.arguments(CreateItemSchema)  # type: ignore[untyped-decorator]
    @blueprint.response(201, ItemResponseSchema, headers=LOCATION)  # type: ignore[untyped-decorator]
    @blueprint.alt_response(404, response="Problem")  # type: ignore[untyped-decorator]
    def create(data: dict[str, Any]) -> tuple[ItemResult, int, dict[str, str]]:
        result = get_item_service().create(**data)
        return result, 201, {"Location": url_for("items.get_one", item_id=result.id)}

    @blueprint.get("/items/<uuid:item_id>")  # type: ignore[untyped-decorator]
    @blueprint.response(200, ItemResponseSchema)  # type: ignore[untyped-decorator]
    @blueprint.alt_response(404, response="Problem")  # type: ignore[untyped-decorator]
    def get_one(item_id: UUID) -> ItemResult:
        return get_item_service().get(item_id)

    @blueprint.put("/items/<uuid:item_id>")  # type: ignore[untyped-decorator]
    @blueprint.arguments(UpdateItemSchema)  # type: ignore[untyped-decorator]
    @blueprint.response(200, ItemResponseSchema)  # type: ignore[untyped-decorator]
    @blueprint.alt_response(404, response="Problem")  # type: ignore[untyped-decorator]
    def update(data: dict[str, Any], item_id: UUID) -> ItemResult:
        return get_item_service().update(item_id, **data)

    @blueprint.delete("/items/<uuid:item_id>")  # type: ignore[untyped-decorator]
    @blueprint.response(204)  # type: ignore[untyped-decorator]
    @blueprint.alt_response(404, response="Problem")  # type: ignore[untyped-decorator]
    def delete(item_id: UUID) -> Response:
        get_item_service().delete(item_id)
        return Response(status=204)

    @blueprint.get("/items/<uuid:item_id>/actions")  # type: ignore[untyped-decorator]
    @blueprint.response(200, ActionResponseSchema(many=True))  # type: ignore[untyped-decorator]
    @blueprint.alt_response(404, response="Problem")  # type: ignore[untyped-decorator]
    def list_actions(item_id: UUID) -> list[ActionResult]:
        return get_action_service().list(item_id)

    @blueprint.post("/items/<uuid:item_id>/actions")  # type: ignore[untyped-decorator]
    @blueprint.arguments(NestedActionSchema)  # type: ignore[untyped-decorator]
    @blueprint.response(201, ActionResponseSchema, headers=LOCATION)  # type: ignore[untyped-decorator]
    @blueprint.alt_response(404, response="Problem")  # type: ignore[untyped-decorator]
    def create_action(
        data: dict[str, Any], item_id: UUID
    ) -> tuple[ActionResult, int, dict[str, str]]:
        result = get_action_service().create(item_id=item_id, **data)
        return result, 201, {"Location": url_for("actions.get_one", action_id=result.id)}

    return blueprint
