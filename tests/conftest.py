"""Shared pytest fixtures. No real database is needed for these tests —
each test that needs a signed-in user monkeypatches app.auth.current_user
instead of hitting Neon.
"""

import pytest

from app import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()
