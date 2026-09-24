"""Provider-independent liveness and operational readiness."""

from flask import Response
from flask_openapi3.blueprint import APIBlueprint
from flask_openapi3.models.tag import Tag

from infra.base import readiness
from infra.resources.db import Database
from infra.resources.redis import RedisCache


def create_health_blueprint(database: Database, cache: RedisCache, prefix: str) -> APIBlueprint:
    blueprint = APIBlueprint(
        "health", __name__, abp_tags=[Tag(name="infra", description="Liveness and readiness")]
    )

    @blueprint.get(
        "/health",
        summary="Check service liveness",
        responses={
            200: {
                "description": "Service is running",
                "content": {"text/plain": {"schema": {"type": "string", "enum": ["Healthy"]}}},
            }
        },
    )
    def health() -> Response:
        return Response("Healthy", status=200, mimetype="text/plain")

    @blueprint.get(
        "/ready",
        summary="Check provider and schema readiness",
        responses={
            200: {
                "description": "Ready; Degraded indicates Redis fallback",
                "content": {
                    "text/plain": {"schema": {"type": "string", "enum": ["Healthy", "Degraded"]}}
                },
            },
            503: {
                "description": "Database or schema is unavailable",
                "content": {"text/plain": {"schema": {"type": "string", "enum": ["Unhealthy"]}}},
            },
        },
    )
    def ready() -> Response:
        result = readiness(database, cache, prefix)
        return Response(result, status=503 if result == "Unhealthy" else 200, mimetype="text/plain")

    return blueprint
