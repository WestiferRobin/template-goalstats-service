"""Flask application factory. Importing this module does not configure providers."""

import logging
import sys
from collections.abc import Mapping
from importlib.util import find_spec

if __name__ == "__main__":
    if sys.version_info[:2] != (3, 12):
        sys.exit("Direct development requires Python 3.12. Run make setup and select .venv.")
    if any(
        find_spec(name) is None
        for name in (
            "flask",
            "flask_smorest",
            "sqlalchemy",
            "psycopg",
            "redis",
            "swagger_ui_bundle",
        )
    ):
        sys.exit(
            "Application dependencies are missing. Run make setup and select .venv/bin/python."
        )

from flask import Flask, Response, send_from_directory
from flask.logging import default_handler
from flask_smorest import Api
from swagger_ui_bundle import swagger_ui_path

from exceptions.handlers import register_error_handlers
from infra.caches.action import ActionCache
from infra.caches.item import ItemCache
from infra.resources.db import Database
from infra.resources.redis import RedisCache
from routers.infra.health import create_health_blueprint
from routers.infra.readiness import create_readiness_blueprint
from routers.item.action import create_actions_blueprint
from routers.item.item import create_items_blueprint
from schemas.infra.problem import ProblemSchema
from settings.base import ConfigurationError, Settings


def create_app(config: Mapping[str, str] | None = None) -> Flask:
    settings = Settings.load(config)
    app = Flask(__name__, static_folder=None)
    app.config.update(
        APP_ENV=settings.app_env,
        TESTING=settings.app_env == "test",
        DEBUG=False,
        API_TITLE="GoalStats Template API",
        API_VERSION="v1",
        OPENAPI_VERSION="3.0.3",
        OPENAPI_URL_PREFIX="/" if settings.openapi_enabled else None,
        OPENAPI_JSON_PATH="swagger/v1/swagger.json",
        OPENAPI_SWAGGER_UI_PATH="swagger",
        OPENAPI_SWAGGER_UI_URL="/swagger-assets/",
    )
    # Logger configuration belongs to this instance, not the process root logger.
    app.logger = logging.Logger("goalstats_template", level=settings.log_level)
    app.logger.addHandler(default_handler)
    app.extensions["goalstats_settings"] = settings
    app.extensions["goalstats_database"] = Database(settings)
    cache = RedisCache(settings, app.logger)
    app.extensions["goalstats_cache"] = cache
    app.extensions["goalstats_item_cache"] = ItemCache(
        cache, settings.cache_key_prefix, settings.cache_ttl_seconds
    )
    app.extensions["goalstats_action_cache"] = ActionCache(
        cache, settings.cache_key_prefix, settings.cache_ttl_seconds
    )
    if settings.redis_url is None:
        app.logger.warning("Redis is unconfigured; database fallback is available")
    if settings.openapi_enabled:

        @app.get("/swagger-assets/<path:filename>")
        def swagger_asset(filename: str) -> Response:
            return send_from_directory(swagger_ui_path, filename)

    api = Api()
    api.DEFAULT_ERROR_RESPONSE_NAME = "Problem"
    api.init_app(app)
    api.spec.components.schema("ProblemDetails", schema=ProblemSchema)
    api.spec.components.response(
        "Problem",
        {
            "description": "Request or application failure",
            "content": {
                "application/problem+json": {
                    "schema": {"$ref": "#/components/schemas/ProblemDetails"}
                }
            },
        },
    )
    app.extensions["goalstats_api"] = api
    # A smorest Blueprint registered with Flask only does not publish operational paths.
    app.register_blueprint(create_health_blueprint())
    app.register_blueprint(create_readiness_blueprint())
    api.register_blueprint(create_items_blueprint())
    api.register_blueprint(create_actions_blueprint())
    register_error_handlers(app)  # Override smorest's default error body contract.
    return app


def development_main() -> None:
    """Direct script execution owns LOCAL configuration; the IDE owns debugging."""
    from settings.host import check_app_port, diagnose_providers, load_host_config

    config = load_host_config()
    port = int(config["HOST_APP_PORT"])
    check_app_port(port)
    app = create_app(config)
    diagnose_providers(app)
    app.run(
        host="127.0.0.1",
        port=port,
        debug=False,
        use_debugger=False,
        use_reloader=False,
        load_dotenv=False,
    )


if __name__ == "__main__":
    try:
        development_main()
    except ConfigurationError as exc:
        sys.exit(str(exc))
