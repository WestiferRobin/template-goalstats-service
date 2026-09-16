"""Safe, uniform errors for Flask, Marshmallow and application failures."""

from http import HTTPStatus

from flask import Flask, Response, current_app, jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException

from exceptions.base import DomainError, RequestValidationError


def problem(status: int, detail: str) -> Response:
    response = jsonify(
        type="about:blank", title=HTTPStatus(status).phrase, status=status, detail=detail
    )
    response.status_code = status
    response.content_type = "application/problem+json"
    return response


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(DomainError)
    def domain_error(error: DomainError) -> Response:
        return problem(error.status, error.public_detail)

    @app.errorhandler(ValidationError)
    def validation_error(error: ValidationError) -> Response:
        # Validator messages can include rejected input; never echo arbitrary messages.
        return problem(400, RequestValidationError.public_detail)

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException) -> Response:
        status = error.code or 500
        detail = {
            400: "The request could not be understood.",
            404: "The requested resource was not found.",
            405: "The request method is not allowed for this resource.",
            415: "The request media type is not supported.",
            422: RequestValidationError.public_detail,
        }.get(
            status, HTTPStatus(status).phrase if status < 500 else "An unexpected error occurred."
        )
        response = problem(status, detail)
        # Preserve routing/retry/auth headers, not the original HTML body metadata.
        for name, value in error.get_response().headers:
            if name.lower() not in {"content-type", "content-length"}:
                response.headers.add(name, value)
        return response

    @app.errorhandler(Exception)
    def unexpected_error(error: Exception) -> Response:
        current_app.logger.error("Unhandled application error (%s)", type(error).__name__)
        return problem(500, "An unexpected error occurred.")
