"""Provider-independent liveness and operational readiness, excluded from OpenAPI."""

from flask import Blueprint, Response

from routers.dependencies import get_cache, get_database, get_settings
from services.readiness import readiness


def create_health_blueprint() -> Blueprint:
    blueprint = Blueprint("health", __name__)

    @blueprint.get("/health")
    def health() -> Response:
        return Response("Healthy", status=200, mimetype="text/plain")

    @blueprint.get("/ready")
    def ready() -> Response:
        result = readiness(get_database(), get_cache(), get_settings().redis.cache_key_prefix)
        return Response(result, status=503 if result == "Unhealthy" else 200, mimetype="text/plain")

    return blueprint
