"""Operational routes; intentionally excluded from the resource OpenAPI document."""

from flask import Response, current_app

from goalstats_template.dependencies import get_database
from goalstats_template.infrastructure.cache.health import is_ready as cache_ready
from goalstats_template.infrastructure.database.health import is_ready
from goalstats_template.routes import ApiBlueprint


def create_meta_blueprint() -> ApiBlueprint:
    blueprint = ApiBlueprint("meta", __name__)

    @blueprint.get("/health")  # type: ignore[untyped-decorator]
    def health() -> Response:
        return Response("Healthy", status=200, mimetype="text/plain")

    @blueprint.get("/ready")  # type: ignore[untyped-decorator]
    def ready() -> Response:
        if not is_ready(get_database()):
            return Response("Unhealthy", status=503, mimetype="text/plain")
        settings = current_app.extensions["goalstats_settings"]
        healthy = cache_ready(current_app.extensions["goalstats_cache"], settings.cache_key_prefix)
        return Response("Healthy" if healthy else "Degraded", status=200, mimetype="text/plain")

    return blueprint
