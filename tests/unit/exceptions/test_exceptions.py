import subprocess
import sys

import pytest

from exceptions.action import ActionNotFound
from exceptions.base import DomainError
from exceptions.item import ItemNotFound


@pytest.mark.parametrize(
    "kind,detail",
    [
        (DomainError, "The operation could not be completed."),
        (ItemNotFound, "Item was not found."),
        (ActionNotFound, "Action was not found."),
    ],
)
def test_private_details_are_not_public(kind, detail):
    error = kind("provider password=private")
    assert isinstance(error, DomainError)
    assert error.public_detail == detail
    assert not hasattr(error, "status")
    assert not hasattr(error, "status_code")
    assert "private" not in error.public_detail


def test_domain_imports_do_not_load_http_handlers():
    subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            "import sys; sys.path.insert(0, 'src'); "
            "import exceptions.item, exceptions.action; "
            "assert 'flask' not in sys.modules; "
            "assert 'exceptions.handlers' not in sys.modules",
        ],
        check=True,
    )
