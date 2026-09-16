from exceptions.base import DomainError, RequestValidationError


def test_domain_private_exception_detail_is_not_public_contract():
    error = DomainError("provider password=private")
    assert error.public_detail == "The operation could not be completed."
    assert error.status == 400
    assert "private" not in error.public_detail


def test_validation_error_has_safe_stable_contract():
    error = RequestValidationError("private input")
    assert error.status == 400
    assert error.public_detail == "The request contains invalid values."
