"""
Who is logged in — , FR-3.

This is foundation, the same as db.py. Every feature that belongs to a
particular student goes through here, so nobody invents their own way of
finding out who is signed in.

    from app.auth import current_user_id, login_required, require_verified

    @bp.get("/watchlist")
    @require_verified
    def watchlist():
        rows = db.query_all(
            "SELECT * FROM watchlists WHERE user_id = %s", (current_user_id(),)
        )
        ...

"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import abort, g, redirect, request, session, url_for

from app import db

COOKIE_KEY = "session_token"


# ---------------------------------------------------------------------
#  Called by FR-3 — login and logout
# ---------------------------------------------------------------------


def start_session(user_id: int) -> str:
    """Create a session row and put its token and Call on login."""
    token = secrets.token_urlsafe(32)
    ttl_hours = int(os.environ.get("SESSION_TTL_HOURS", "72"))
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

    db.execute(
        "INSERT INTO sessions (user_id, token, expires_at) VALUES (%s, %s, %s)",
        (user_id, token, expires_at),
    )
    session[COOKIE_KEY] = token
    session.permanent = True
    return token


def end_session() -> None:
    """Delete the session row and clear the cookie. Call on logout."""
    token = session.pop(COOKIE_KEY, None)
    if token:
        db.execute("DELETE FROM sessions WHERE token = %s", (token,))


# ---------------------------------------------------------------------
#  Called by everyone else
# ---------------------------------------------------------------------


def current_user() -> dict | None:
    """
    The signed-in user's row, or None.

    Cached on `g` so several calls in one request hit the database once.
    `g` is cleared automatically at the end of each request.
    """
    if "user" in g:
        return g.user

    g.user = None
    token = session.get(COOKIE_KEY)
    if not token:
        return None

    row = db.query_one(
        """
        SELECT u.id, u.first_name, u.last_name, u.email, u.verified, s.expires_at
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = %s
        """,
        (token,),
    )
    if row is None:
        return None

    if row["expires_at"] < datetime.now(timezone.utc):
        db.execute("DELETE FROM sessions WHERE token = %s", (token,))
        session.pop(COOKIE_KEY, None)
        return None

    db.execute("UPDATE sessions SET last_active = NOW() WHERE token = %s", (token,))
    g.user = row
    return row


def current_user_id() -> int | None:
    user = current_user()
    return user["id"] if user else None


def login_required(view):
    """Signed in. Use for anything that belongs to a particular student."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("auth.login_form", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def require_verified(view):
    """
    Signed in AND the unt.edu address confirmed (FR-2).

    This is the one to use on listings, messaging and the watchlist.
    An unverified account must not be able to act in the marketplace.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            return redirect(url_for("auth.login_form", next=request.path))
        if not user["verified"]:
            abort(403, "Confirm your UNT email address before using this feature.")
        return view(*args, **kwargs)

    return wrapped


# ---------------------------------------------------------------------
#  Temporary — delete once FR-3 login is merged.
#
#  Set DEV_LOGIN_AS=1 in your .env and every request is treated as
#  user 1. This lets the rest of us build and test our features before
#  the login page exists. It only works when FLASK_DEBUG is on, so it
#  cannot be switched on by accident in production.
# ---------------------------------------------------------------------


def dev_login_if_enabled(app) -> None:
    dev_user = os.environ.get("DEV_LOGIN_AS")
    if not dev_user or not app.debug:
        return

    @app.before_request
    def _fake_login():
        g.user = db.query_one(
            "SELECT id, first_name, last_name, email, verified FROM users WHERE id = %s",
            (int(dev_user),),
        )

    app.logger.warning("DEV_LOGIN_AS is on — every request is user %s", dev_user)
