"""Action HTTP operations; explicit typed validation and serialization."""

from flask import Response, jsonify, url_for
from flask_openapi3.blueprint import APIBlueprint
from flask_openapi3.models.tag import Tag

from exceptions.handlers import object_body
from routers.openapi import created_response, errors
from schemas.action.base import ActionPathSchema
from schemas.action.request import ActionCreateRequest, ActionWriteRequest
from schemas.action.response import ActionListResponse, ActionResponse
from schemas.item.base import ItemPathSchema
from services.action import ActionService


def create_actions_blueprint(service: ActionService) -> APIBlueprint:
    blueprint = APIBlueprint(
        "actions",
        __name__,
        abp_tags=[Tag(name="actions", description="Action reference resources")],
        abp_responses=errors(),
    )
    blueprint.before_request(object_body)

    @blueprint.get("/actions", responses={200: ActionListResponse})
    def list_all() -> Response:
        return jsonify(ActionListResponse(service.list()).model_dump(mode="json", by_alias=True))

    @blueprint.post(
        "/actions", responses={201: created_response(ActionResponse), 404: errors()["default"]}
    )
    def create(body: ActionCreateRequest) -> Response:
        result = service.create(body)
        response = jsonify(result.model_dump(mode="json", by_alias=True))
        response.status_code = 201
        response.headers["Location"] = url_for("actions.get_one", action_id=result.id)
        return response

    @blueprint.get(
        "/actions/<uuid:action_id>", responses={200: ActionResponse, 404: errors()["default"]}
    )
    def get_one(path: ActionPathSchema) -> Response:
        return jsonify(service.get(path.action_id).model_dump(mode="json", by_alias=True))

    @blueprint.put(
        "/actions/<uuid:action_id>", responses={200: ActionResponse, 404: errors()["default"]}
    )
    def update(path: ActionPathSchema, body: ActionWriteRequest) -> Response:
        return jsonify(service.update(path.action_id, body).model_dump(mode="json", by_alias=True))

    @blueprint.delete("/actions/<uuid:action_id>", responses={204: None, 404: errors()["default"]})
    def delete(path: ActionPathSchema) -> Response:
        service.delete(path.action_id)
        return Response(status=204)

    @blueprint.get(
        "/items/<uuid:item_id>/actions",
        responses={200: ActionListResponse, 404: errors()["default"]},
    )
    def list_actions(path: ItemPathSchema) -> Response:
        return jsonify(
            ActionListResponse(service.list(path.item_id)).model_dump(mode="json", by_alias=True)
        )

    @blueprint.post(
        "/items/<uuid:item_id>/actions",
        responses={201: created_response(ActionResponse), 404: errors()["default"]},
    )
    def create_action(path: ItemPathSchema, body: ActionWriteRequest) -> Response:
        command = ActionCreateRequest.model_validate(
            {**body.model_dump(by_alias=True), "itemId": path.item_id}
        )
        result = service.create(command)
        response = jsonify(result.model_dump(mode="json", by_alias=True))
        response.status_code = 201
        response.headers["Location"] = url_for("actions.get_one", action_id=result.id)
        return response

    return blueprint
