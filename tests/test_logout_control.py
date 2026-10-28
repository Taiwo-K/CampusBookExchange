"""
The global logout control in base.html: every page should show
"Sign out" when a session is active, and a sign-in link otherwise —
driven by the current_user() context processor in app/__init__.py.
"""

import pytest

from app import auth, create_app


@pytest.fixture
def client(monkeypatch):
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_signed_out_search_page_shows_sign_in_link(client, monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda: None)

    response = client.get("/search")

    assert response.status_code == 200
    assert b"Sign in" in response.data
    assert b"Sign out" not in response.data


def test_signed_in_search_page_shows_sign_out_control(client, monkeypatch):
    monkeypatch.setattr(
        auth,
        "current_user",
        lambda: {"id": 1, "first_name": "Jess", "last_name": "P", "verified": True},
    )

    response = client.get("/search")

    assert response.status_code == 200
    assert b"Sign out" in response.data
    assert b"Jess" in response.data


def test_sign_out_form_posts_to_logout(client, monkeypatch):
    monkeypatch.setattr(
        auth,
        "current_user",
        lambda: {"id": 1, "first_name": "Jess", "last_name": "P", "verified": True},
    )

    response = client.get("/search")

    assert b'action="/logout"' in response.data
    assert b'method="POST"' in response.data
