from typing import Any
from uuid import UUID

from flask import Response, url_for

from composition import get_action_service
from routers import ApiBlueprint
from schemas.action.base import ActionResult
from schemas.action.request import CreateActionSchema, UpdateActionSchema
from schemas.action.response import ActionResponseSchema

LOCATION = {"Location": {"description": "Canonical resource URL", "schema": {"type": "string"}}}


def create_actions_blueprint() -> ApiBlueprint:
    blueprint = ApiBlueprint("actions", __name__, description="Action reference resources")

    @blueprint.get("/actions")  # type: ignore[untyped-decorator]
    @blueprint.response(200, ActionResponseSchema(many=True))  # type: ignore[untyped-decorator]
    def list_all() -> list[ActionResult]:
        return get_action_service().list()

    @blueprint.post("/actions")  # type: ignore[untyped-decorator]
    @blueprint.arguments(CreateActionSchema)  # type: ignore[untyped-decorator]
    @blueprint.response(201, ActionResponseSchema, headers=LOCATION)  # type: ignore[untyped-decorator]
    @blueprint.alt_response(404, response="Problem")  # type: ignore[untyped-decorator]
    def create(data: dict[str, Any]) -> tuple[ActionResult, int, dict[str, str]]:
        result = get_action_service().create(**data)
        return result, 201, {"Location": url_for("actions.get_one", action_id=result.id)}

    @blueprint.get("/actions/<uuid:action_id>")  # type: ignore[untyped-decorator]
    @blueprint.response(200, ActionResponseSchema)  # type: ignore[untyped-decorator]
    @blueprint.alt_response(404, response="Problem")  # type: ignore[untyped-decorator]
    def get_one(action_id: UUID) -> ActionResult:
        return get_action_service().get(action_id)

    @blueprint.put("/actions/<uuid:action_id>")  # type: ignore[untyped-decorator]
    @blueprint.arguments(UpdateActionSchema)  # type: ignore[untyped-decorator]
    @blueprint.response(200, ActionResponseSchema)  # type: ignore[untyped-decorator]
    @blueprint.alt_response(404, response="Problem")  # type: ignore[untyped-decorator]
    def update(data: dict[str, Any], action_id: UUID) -> ActionResult:
        return get_action_service().update(action_id, **data)

    @blueprint.delete("/actions/<uuid:action_id>")  # type: ignore[untyped-decorator]
    @blueprint.response(204)  # type: ignore[untyped-decorator]
    @blueprint.alt_response(404, response="Problem")  # type: ignore[untyped-decorator]
    def delete(action_id: UUID) -> Response:
        get_action_service().delete(action_id)
        return Response(status=204)

    return blueprint
