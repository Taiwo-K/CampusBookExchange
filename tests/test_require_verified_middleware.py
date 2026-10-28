"""
FR-2 — the app-wide verification guard in app.auth.register_verification_guard.

These exercise the *middleware*, not the @require_verified decorator
(that one is covered by exercising listings directly once it is wired
up). The point of the guard is that a brand new blueprint is blocked
by default even if nobody remembers to decorate its routes, so the
routes here are a throwaway blueprint built in the test itself rather
than any real feature blueprint.
"""

from flask import Blueprint


def _add_unprotected_test_route(app):
    """A route on a blueprint with no @require_verified anywhere, to
    prove the guard — not the decorator — is what blocks it."""
    bp = Blueprint("widgets", __name__)

    @bp.get("/widgets")
    def widgets():
        return "widgets ok"

    app.register_blueprint(bp)


def test_signed_out_user_is_redirected_to_login(app, client):
    _add_unprotected_test_route(app)

    response = client.get("/widgets")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_unverified_user_gets_403(app, client, monkeypatch):
    _add_unprotected_test_route(app)
    monkeypatch.setattr(
        "app.auth.current_user",
        lambda: {"id": 1, "email": "student@unt.edu", "verified": False},
    )

    response = client.get("/widgets")

    assert response.status_code == 403


def test_verified_user_passes_through(app, client, monkeypatch):
    _add_unprotected_test_route(app)
    monkeypatch.setattr(
        "app.auth.current_user",
        lambda: {"id": 1, "email": "student@unt.edu", "verified": True},
    )

    response = client.get("/widgets")

    assert response.status_code == 200
    assert response.data == b"widgets ok"


def test_public_blueprint_is_reachable_without_login(client):
    """auth, verify and search stay open — registration/verification
    have to work before anyone can be verified."""
    response = client.get("/resend-verification")

    assert response.status_code == 200


def test_blueprintless_route_is_not_blocked_by_the_guard(client):
    """/api/health is defined on the app, not a blueprint — the guard
    must not swallow it, regardless of whether the database answers."""
    response = client.get("/api/health")

    assert response.status_code in (200, 503)
