"""
Accounts — FR-1 registration, FR-2 verification, FR-3 login.

SKELETON ONLY. The GET routes render the pages so the app runs end to
end from day one. 
"""

import re

import bcrypt
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
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
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")

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


@bp.get("/login")
def login_form():
    # TODO (FR-3): build templates/login.html from the Figma login screen.
    return "Login page not built yet", 501
