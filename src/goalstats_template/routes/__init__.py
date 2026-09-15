"""HTTP adapters use one validation status contract."""

from flask_smorest import Blueprint
from webargs.flaskparser import FlaskParser


class RequestParser(FlaskParser):
    DEFAULT_VALIDATION_STATUS = 400


# flask-smorest does not ship typing metadata; isolate its untyped boundary here.
class ApiBlueprint(Blueprint):  # type: ignore[misc]
    ARGUMENTS_PARSER = RequestParser()
