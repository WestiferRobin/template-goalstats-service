"""Provider-independent liveness and operational readiness, excluded from OpenAPI."""

from flask import Blueprint, Response

from infra.base import readiness
from infra.resources.db import Database
from infra.resources.redis import RedisCache


def create_health_blueprint(database: Database, cache: RedisCache, prefix: str) -> Blueprint:
    blueprint = Blueprint("health", __name__)

    @blueprint.get("/health")
    def health() -> Response:
        return Response("Healthy", status=200, mimetype="text/plain")

    @blueprint.get("/ready")
    def ready() -> Response:
        result = readiness(database, cache, prefix)
        return Response(result, status=503 if result == "Unhealthy" else 200, mimetype="text/plain")

    return blueprint
