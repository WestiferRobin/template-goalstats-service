"""Generated OpenAPI and local Swagger assets; no independently maintained schema."""

from importlib.resources import files
from typing import Any

from flask import Blueprint, Response, jsonify, send_from_directory
from flask_openapi3.openapi import OpenAPI
from flask_openapi3.types import ResponseDict
from pydantic import BaseModel


def errors() -> ResponseDict:
    problem = {
        "description": "Request or application failure",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ProblemDetailSchema"}
            }
        },
    }
    return {"default": problem, "400": problem}


def created_response(model: type[BaseModel]) -> dict[str, Any]:
    # Generate the 201 schema from the same model used by the typed 200 response.
    return {
        "description": "Created",
        "headers": {
            "Location": {"description": "Canonical resource URL", "schema": {"type": "string"}}
        },
        "content": {
            "application/json": {
                "schema": model.model_json_schema(
                    mode="serialization", ref_template="#/components/schemas/{model}"
                )
            }
        },
    }


def create_docs_blueprint(app: OpenAPI) -> Blueprint:
    blueprint = Blueprint("docs", __name__)

    @blueprint.get("/swagger/v1/swagger.json")
    def spec() -> Response:
        return jsonify(app.api_doc)

    @blueprint.get("/swagger")
    def swagger() -> str:
        return (
            '<link rel="stylesheet" href="/swagger-assets/swagger-ui.css">'
            '<div id="swagger-ui"></div>'
            '<script src="/swagger-assets/swagger-ui-bundle.js"></script>'
            '<script>SwaggerUIBundle({url:"/swagger/v1/swagger.json",dom_id:"#swagger-ui"})</script>'
        )

    @blueprint.get("/swagger-assets/<path:filename>")
    def asset(filename: str) -> Response:
        directory = "css" if filename.endswith(".css") else "js"
        asset_root = files("flask_openapi3_swagger").joinpath("templates", "swagger", directory)
        return send_from_directory(str(asset_root), filename)

    return blueprint
