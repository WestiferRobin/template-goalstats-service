from errors import DomainError, RequestValidationError


def test_domain_private_exception_detail_is_not_public_contract():
    error = DomainError("provider password=private")
    assert error.public_detail == "The operation could not be completed."
    assert not hasattr(error, "status")
    assert "private" not in error.public_detail


def test_validation_error_has_safe_stable_contract():
    error = RequestValidationError("private input")
    assert not hasattr(error, "status")
    assert error.public_detail == "The request contains invalid values."
