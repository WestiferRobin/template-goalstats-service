"""Provider-independent liveness, excluded from resource OpenAPI."""

from flask import Response

from routers import ApiBlueprint


def create_health_blueprint() -> ApiBlueprint:
    blueprint = ApiBlueprint("health", __name__)

    @blueprint.get("/health")  # type: ignore[untyped-decorator]
    def health() -> Response:
        return Response("Healthy", status=200, mimetype="text/plain")

    return blueprint
