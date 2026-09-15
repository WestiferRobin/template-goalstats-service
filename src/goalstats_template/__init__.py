"""Flask application factory. Importing this module does not configure providers."""

import logging
from collections.abc import Mapping

from flask import Flask, Response, send_from_directory
from flask.logging import default_handler
from flask_smorest import Api
from swagger_ui_bundle import swagger_ui_path

from goalstats_template.config import Settings
from goalstats_template.dependencies import close_session
from goalstats_template.errors import ProblemSchema, register_error_handlers
from goalstats_template.infrastructure.cache.actions import ActionCache
from goalstats_template.infrastructure.cache.items import ItemCache
from goalstats_template.infrastructure.cache.redis_cache import RedisCache
from goalstats_template.infrastructure.database.session import Database
from goalstats_template.routes.actions import create_actions_blueprint
from goalstats_template.routes.items import create_items_blueprint
from goalstats_template.routes.meta import create_meta_blueprint


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
    app.register_blueprint(create_meta_blueprint())
    api.register_blueprint(create_items_blueprint())
    api.register_blueprint(create_actions_blueprint())
    register_error_handlers(app)  # Override smorest's default error body contract.
    app.teardown_appcontext(close_session)
    return app
