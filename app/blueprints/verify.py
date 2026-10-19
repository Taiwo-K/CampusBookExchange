"""
Email verification — FR-2.


Two routes:
    GET  /verify?token=...     the link in the email
    GET  /resend-verification  the form
    POST /resend-verification  sends a fresh link
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.services.email import resend_verification, verify_token

bp = Blueprint("verify", __name__)


@bp.get("/verify")
def verify():
    """
    The link in the email lands here.
    """
    raw_token = request.args.get("token", "").strip()

    if not raw_token:
        return render_template(
            "verify_result.html",
            ok=False,
            heading="That link is incomplete",
            detail="Open the link straight from your email rather than "
                   "copying part of it.",
        ), 400

    user_id = verify_token(raw_token)

    if user_id is None:
        # Expired, already used, or never existed.
        # — a stranger with a guessed token shouldn't
        # learn whether it was close.
        return render_template(
            "verify_result.html",
            ok=False,
            heading="That link has expired",
            detail="Verification links last 24 hours and work once. "
                   "Request a new one below.",
            show_resend=True,
        ), 400

    user = db.query_one(
        "SELECT first_name FROM users WHERE id = %s", (user_id,)
    )
    return render_template(
        "verify_result.html",
        ok=True,
        heading="You're verified",
        detail=f"Thanks{', ' + user['first_name'] if user else ''} — "
               "your UNT address is confirmed. You can now post listings "
               "and message other students.",
    )


@bp.get("/resend-verification")
def resend_form():
    return render_template("resend.html")


@bp.post("/resend-verification")
def resend_submit():
    """
    FR-2 alternate flow.

    This always reports success, whether or not the address exists or
    is already verified.
    """
    email = request.form.get("email", "").strip()

    if not email:
        flash("Enter your UNT email address.", "error")
        return render_template("resend.html"), 400

    resend_verification(email)

    flash(
        "If that address needs verifying, a new link is on its way. "
        "It expires in 24 hours.",
        "ok",
    )
    return redirect(url_for("verify.resend_form"))
