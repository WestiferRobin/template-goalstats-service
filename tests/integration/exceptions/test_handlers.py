import pytest
from flask import request
from marshmallow import Schema, ValidationError, fields
from werkzeug.exceptions import BadRequest

from exceptions.base import DomainError
from routers import ApiBlueprint


@pytest.fixture
def error_app(app):
    # Test-only routes exercise real Flask/Marshmallow boundaries, never production debug routes.
    blueprint = ApiBlueprint("boundary_test", __name__)

    class InputSchema(Schema):
        name = fields.String(required=True)

    @blueprint.post("/_validation")
    @blueprint.arguments(InputSchema)
    @blueprint.response(200, InputSchema)
    def validate(data):
        return data

    @app.post("/_json")
    def json_body():
        return request.get_json()

    @app.get("/_domain")
    def domain():
        raise DomainError("SQL private_password")

    @app.get("/_marshmallow")
    def marshmallow():
        raise ValidationError("private_password")

    @app.get("/_http")
    def http():
        raise BadRequest("private_password")

    @app.get("/_unexpected")
    def unexpected():
        raise RuntimeError("SQL private_password")

    app.extensions["goalstats_api"].register_blueprint(blueprint)
    return app


@pytest.mark.parametrize(
    "path,method,status",
    [
        ("/missing", "get", 404),
        ("/health", "post", 405),
        ("/_domain", "get", 400),
        ("/_marshmallow", "get", 400),
        ("/_http", "get", 400),
        ("/_unexpected", "get", 500),
    ],
)
def test_consistent_safe_problem_details(error_app, path, method, status, capsys):
    response = getattr(error_app.test_client(), method)(path, headers={"Accept": "text/html"})
    assert response.status_code == status
    assert response.mimetype == "application/problem+json"
    assert set(response.json) == {"type", "title", "status", "detail"}
    assert response.json["status"] == status
    assert response.json["type"] == "about:blank"
    assert "private_password" not in response.text
    assert "private_password" not in capsys.readouterr().err
    if status == 405:
        assert {"GET", "HEAD", "OPTIONS"} <= set(
            response.headers["Allow"].replace(" ", "").split(",")
        )


@pytest.mark.parametrize("path", ["/_json", "/_validation"])
def test_malformed_json_uses_problem_details(error_app, path):
    response = error_app.test_client().post(
        path, data="{broken private_password", content_type="application/json"
    )
    assert response.status_code == 400
    assert response.mimetype == "application/problem+json"
    assert "private_password" not in response.text


def test_smorest_validation_uses_400_and_unknown_fields_are_rejected(error_app):
    client = error_app.test_client()
    for data in [{}, {"name": "valid", "unexpected": "private_password"}]:
        response = client.post("/_validation", json=data)
        assert response.status_code == 400
        assert response.mimetype == "application/problem+json"
        assert "private_password" not in response.text
    assert client.post("/_validation", json={"name": "valid"}).json == {"name": "valid"}


def test_non_json_body_is_safe_415(error_app):
    response = error_app.test_client().post(
        "/_json", data="private_password", content_type="text/plain"
    )
    assert response.status_code == 415
    assert response.mimetype == "application/problem+json"
    assert "private_password" not in response.text
