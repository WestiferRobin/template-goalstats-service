"""Action HTTP operations; explicit typed validation and serialization."""

from flask import Response, jsonify, url_for
from flask_openapi3.blueprint import APIBlueprint
from flask_openapi3.models.tag import Tag

from routers.dependencies import get_action_service
from routers.errors import object_body
from routers.openapi import created_response, errors
from schemas.action import ActionCreate, ActionListResponse, ActionPath, ActionResponse, ActionWrite
from schemas.item import ItemPath


def create_actions_blueprint() -> APIBlueprint:
    blueprint = APIBlueprint(
        "actions",
        __name__,
        abp_tags=[Tag(name="actions", description="Action reference resources")],
        abp_responses=errors(),
    )
    blueprint.before_request(object_body)

    @blueprint.get("/actions", responses={200: ActionListResponse})
    def list_all() -> Response:
        return jsonify(
            ActionListResponse(get_action_service().list()).model_dump(mode="json", by_alias=True)
        )

    @blueprint.post(
        "/actions", responses={201: created_response(ActionResponse), 404: errors()["default"]}
    )
    def create(body: ActionCreate) -> Response:
        result = get_action_service().create(body)
        response = jsonify(result.model_dump(mode="json", by_alias=True))
        response.status_code = 201
        response.headers["Location"] = url_for("actions.get_one", action_id=result.id)
        return response

    @blueprint.get(
        "/actions/<uuid:action_id>", responses={200: ActionResponse, 404: errors()["default"]}
    )
    def get_one(path: ActionPath) -> Response:
        return jsonify(
            get_action_service().get(path.action_id).model_dump(mode="json", by_alias=True)
        )

    @blueprint.put(
        "/actions/<uuid:action_id>", responses={200: ActionResponse, 404: errors()["default"]}
    )
    def update(path: ActionPath, body: ActionWrite) -> Response:
        return jsonify(
            get_action_service().update(path.action_id, body).model_dump(mode="json", by_alias=True)
        )

    @blueprint.delete("/actions/<uuid:action_id>", responses={204: None, 404: errors()["default"]})
    def delete(path: ActionPath) -> Response:
        get_action_service().delete(path.action_id)
        return Response(status=204)

    @blueprint.get(
        "/items/<uuid:item_id>/actions",
        responses={200: ActionListResponse, 404: errors()["default"]},
    )
    def list_actions(path: ItemPath) -> Response:
        return jsonify(
            ActionListResponse(get_action_service().list(path.item_id)).model_dump(
                mode="json", by_alias=True
            )
        )

    @blueprint.post(
        "/items/<uuid:item_id>/actions",
        responses={201: created_response(ActionResponse), 404: errors()["default"]},
    )
    def create_action(path: ItemPath, body: ActionWrite) -> Response:
        command = ActionCreate.model_validate(
            {**body.model_dump(by_alias=True), "itemId": path.item_id}
        )
        result = get_action_service().create(command)
        response = jsonify(result.model_dump(mode="json", by_alias=True))
        response.status_code = 201
        response.headers["Location"] = url_for("actions.get_one", action_id=result.id)
        return response

    return blueprint
