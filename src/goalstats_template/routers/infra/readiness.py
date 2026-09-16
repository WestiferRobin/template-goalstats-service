"""Operational readiness HTTP adapter, excluded from resource OpenAPI."""

from flask import Response

from goalstats_template.composition import get_cache, get_database, get_settings
from goalstats_template.routers import ApiBlueprint
from goalstats_template.services.infra import readiness


def create_readiness_blueprint() -> ApiBlueprint:
    blueprint = ApiBlueprint("readiness", __name__)

    @blueprint.get("/ready")  # type: ignore[untyped-decorator]
    def ready() -> Response:
        result = readiness(get_database(), get_cache(), get_settings().cache_key_prefix)
        return Response(result, status=503 if result == "Unhealthy" else 200, mimetype="text/plain")

    return blueprint
