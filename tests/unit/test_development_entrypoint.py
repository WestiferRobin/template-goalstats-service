"""Direct development execution delegates once and never owns the debugger."""

from unittest.mock import Mock

import pytest

import main
from settings.base import ConfigurationError


@pytest.mark.parametrize("port,expected", [(None, 5300), ("54321", 54321)])
def test_direct_local_constructs_once_without_reloader_or_dotenv(monkeypatch, port, expected):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("FLASK_DEBUG", "1")
    if port is None:
        monkeypatch.delenv("HOST_APP_PORT", raising=False)
    else:
        monkeypatch.setenv("HOST_APP_PORT", port)
    factory = Mock()
    monkeypatch.setattr(main, "create_app", factory)
    main.development_main()
    factory.assert_called_once_with()
    factory.return_value.run.assert_called_once_with(
        host="127.0.0.1",
        port=expected,
        debug=False,
        use_debugger=False,
        use_reloader=False,
        load_dotenv=False,
    )


@pytest.mark.parametrize("environment", [None, "dev", "test", "production", ""])
def test_direct_refuses_nonlocal_before_constructing_app(monkeypatch, environment):
    if environment is None:
        monkeypatch.delenv("APP_ENV", raising=False)
    else:
        monkeypatch.setenv("APP_ENV", environment)
    factory = Mock()
    monkeypatch.setattr(main, "create_app", factory)
    with pytest.raises(ConfigurationError, match="APP_ENV"):
        main.development_main()
    factory.assert_not_called()


@pytest.mark.parametrize("port", ["0", "65536", "-1", "abc", "", "53.0", " 5300", "５３００"])
def test_direct_refuses_invalid_port_before_construction(monkeypatch, port):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOST_APP_PORT", port)
    factory = Mock()
    monkeypatch.setattr(main, "create_app", factory)
    with pytest.raises(ConfigurationError, match="HOST_APP_PORT"):
        main.development_main()
    factory.assert_not_called()
