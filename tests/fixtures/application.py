from collections.abc import Callable, Iterator, Mapping

import pytest
from flask import Flask

from main import create_app


@pytest.fixture
def app_factory() -> Iterator[Callable[[Mapping[str, str]], Flask]]:
    apps = []

    def make(config: Mapping[str, str]) -> Flask:
        app = create_app(config)
        apps.append(app)
        return app

    yield make
    for app in apps:
        app.extensions["goalstats_cache"].close()
        app.extensions["goalstats_database"].dispose()


@pytest.fixture
def app(app_factory, explicit_config) -> Flask:
    return app_factory(explicit_config)
