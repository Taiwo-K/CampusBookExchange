"""
Accounts — FR-1 registration, FR-2 verification, FR-3 login.

SKELETON ONLY. The GET routes render the pages so the app runs end to
end from day one. 
"""

import re

import bcrypt
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app import db
from app.auth import end_session, start_session
from app.password_validator import validate_password
from app.services.email import send_verification

bp = Blueprint("auth", __name__)

# Same rule as the browser check in register.html, and as the
# users_email_is_unt constraint in db/schema.sql. All three have to
# agree. The database one is the only one that cannot be bypassed.
UNT_EMAIL = re.compile(r"^[^@\s]+@([a-z0-9-]+\.)*unt\.edu$", re.IGNORECASE)


@bp.get("/register")
def register_form():
    return render_template("register.html")


@bp.post("/register")
def register_submit():
    """
    FR-1. TODO — owner of the registration task.

    The browser already checks these fields, but that check is for the
    user's convenience only. This is the part that is actually security.
    """
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    errors = []
    if not first_name:
        errors.append("First name is required.")
    if not last_name:
        errors.append("Last name is required.")
    if not UNT_EMAIL.match(email):
        errors.append("Use your unt.edu email address.")
    errors.extend(validate_password(password, email, first_name, last_name))

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("register.html", form=request.form), 400

    # Never store the password itself. bcrypt turns it into a hash that
    # cannot be reversed, and the cost factor makes guessing slow.
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

    existing = db.query_one("SELECT id FROM users WHERE email = %s", (email,))
    if existing:
        # Deliberately vague: saying "that email is taken" tells a
        # stranger who has an account here.
        flash("If that address is eligible, a verification email is on its way.", "info")
        return redirect(url_for("auth.register_form"))

    user = db.execute(
        """
        INSERT INTO users (first_name, last_name, email, password_hash)
        VALUES (%s, %s, %s, %s)
        RETURNING id, email
        """,
        (first_name, last_name, email, password_hash),
    )

    # TODO (FR-2): 
    send_verification(user["id"], user["email"])
    

    flash("Account created. Check your UNT email for the verification link.", "ok")
    return redirect(url_for("auth.register_form"))


# Checked against when the email is unknown, so a login for a missing
# account takes as long as one with a wrong password. Without it the
# response time would reveal which unt.edu addresses have accounts.
_dummy_hash: bytes | None = None


def _get_dummy_hash() -> bytes:
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt(rounds=12))
    return _dummy_hash


def _safe_next(target: str | None) -> str | None:
    """Only allow redirects to a path on this site, never another domain."""
    if not target or not target.startswith("/"):
        return None
    if target.startswith("//") or "\\" in target:
        return None
    return target


@bp.get("/login")
def login_form():
    return render_template("login.html", next=request.args.get("next", ""))


@bp.post("/login")
def login_submit():
    """
    FR-3. Check the email and password, then open a session.

    The error is the same whether the email or the password was wrong,
    so the form cannot be used to find out who has an account.
    """
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    next_url = request.form.get("next", "")

    user = None
    if email and password:
        user = db.query_one(
            "SELECT id, password_hash, verified FROM users WHERE email = %s", (email,)
        )

    stored = user["password_hash"].encode() if user else _get_dummy_hash()
    password_ok = bcrypt.checkpw(password.encode(), stored)

    if user is None or not password_ok:
        flash("Invalid email or password.", "error")
        return render_template("login.html", form=request.form, next=next_url), 401

    # Drop anything left in the cookie from before, then start fresh.
    session.clear()
    start_session(user["id"])

    if not user["verified"]:
        flash("Signed in. Confirm your UNT email to use the marketplace.", "info")
    return redirect(_safe_next(next_url) or url_for("auth.login_form"))


@bp.post("/logout")
def logout():
    end_session()
    flash("You have been signed out.", "ok")
    return redirect(url_for("auth.login_form"))
