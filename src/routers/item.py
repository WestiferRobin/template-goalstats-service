"""Item HTTP operations; explicit typed validation and serialization."""

from flask import Response, jsonify, url_for
from flask_openapi3.blueprint import APIBlueprint
from flask_openapi3.models.tag import Tag

from exceptions.handlers import object_body
from routers.openapi import created_response, errors
from schemas.item.base import ItemPathSchema
from schemas.item.request import ItemCreateRequest, ItemUpdateRequest
from schemas.item.response import ItemListResponse, ItemResponse
from services.item import ItemService


def create_items_blueprint(service: ItemService) -> APIBlueprint:
    blueprint = APIBlueprint(
        "items",
        __name__,
        abp_tags=[Tag(name="items", description="Item reference resources")],
        abp_responses=errors(),
    )
    blueprint.before_request(object_body)

    @blueprint.get("/items", responses={200: ItemListResponse})
    def list_all() -> Response:
        return jsonify(ItemListResponse(service.list()).model_dump(mode="json", by_alias=True))

    @blueprint.post(
        "/items", responses={201: created_response(ItemResponse), 404: errors()["default"]}
    )
    def create(body: ItemCreateRequest) -> Response:
        result = service.create(body)
        response = jsonify(result.model_dump(mode="json", by_alias=True))
        response.status_code = 201
        response.headers["Location"] = url_for("items.get_one", item_id=result.id)
        return response

    @blueprint.get("/items/<uuid:item_id>", responses={200: ItemResponse, 404: errors()["default"]})
    def get_one(path: ItemPathSchema) -> Response:
        return jsonify(service.get(path.item_id).model_dump(mode="json", by_alias=True))

    @blueprint.put("/items/<uuid:item_id>", responses={200: ItemResponse, 404: errors()["default"]})
    def update(path: ItemPathSchema, body: ItemUpdateRequest) -> Response:
        return jsonify(service.update(path.item_id, body).model_dump(mode="json", by_alias=True))

    @blueprint.delete("/items/<uuid:item_id>", responses={204: None, 404: errors()["default"]})
    def delete(path: ItemPathSchema) -> Response:
        service.delete(path.item_id)
        return Response(status=204)

    return blueprint
