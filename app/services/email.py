"""
Email delivery — FR-2 verification, FR-13 watchlist alerts.

Everything that sends mail goes through this file. The rest of the app
never talks to Resend directly, 
In development set EMAIL_DEV_LOG_ONLY=true in .env and the links print
to the terminal instead of being sent. 
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from app import db


def _dev_log_only() -> bool:
    return os.environ.get("EMAIL_DEV_LOG_ONLY", "true").lower() == "true"


def _send(to: str, subject: str, html: str) -> None:
    """The single place a real message leaves the application."""
    if _dev_log_only():
        print("\n" + "=" * 60)
        print(f"  EMAIL (not actually sent — EMAIL_DEV_LOG_ONLY is true)")
        print(f"  To:      {to}")
        print(f"  Subject: {subject}")
        print("-" * 60)
        print(html)
        print("=" * 60 + "\n")
        return

    import resend

    resend.api_key = os.environ["RESEND_API_KEY"]
    resend.Emails.send(
        {
            "from": os.environ["EMAIL_FROM"],
            "to": to,
            "subject": subject,
            "html": html,
        }
    )


# ---------------------------------------------------------------------
#  FR-2 — verification
# ---------------------------------------------------------------------


def create_verification_token(user_id: int) -> str:
    """
    Make a one-time token, store only its hash, return the raw value.

    The raw token goes in the email and nowhere else. We store the hash
    so that someone who reads the verification_tokens table still cannot
    verify anyone's account — the same reason we hash passwords.
    """
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()

    ttl_hours = int(os.environ.get("VERIFICATION_TOKEN_TTL_HOURS", "24"))
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

    # Any older token for this user stops working the moment a new one
    # is issued, so a forwarded old email is useless.
    db.execute("DELETE FROM verification_tokens WHERE user_id = %s", (user_id,))
    db.execute(
        """
        INSERT INTO verification_tokens (user_id, token_hash, expires_at)
        VALUES (%s, %s, %s)
        """,
        (user_id, token_hash, expires_at),
    )
    return raw


def send_verification(user_id: int, email: str) -> None:
    raw = create_verification_token(user_id)
    base = os.environ.get("APP_BASE_URL", "http://localhost:5000")
    link = f"{base}/verify?token={raw}"

    _send(
        to=email,
        subject="Confirm your CampusBookExchange account",
        html=(
            "<p>Welcome to CampusBookExchange.</p>"
            f'<p><a href="{link}">Confirm your account</a></p>'
            "<p>This link expires in 24 hours. If you did not create an "
            "account, you can ignore this message.</p>"
        ),
    )


def verify_token(raw_token: str) -> int | None:
    """
    Check a token and mark the account verified.

    Returns the user id on success, None if the token is unknown,
    already used, or expired.
    """
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    row = db.query_one(
        """
        SELECT user_id, expires_at
        FROM verification_tokens
        WHERE token_hash = %s
        """,
        (token_hash,),
    )
    if row is None:
        return None

    if row["expires_at"] < datetime.now(timezone.utc):
        db.execute("DELETE FROM verification_tokens WHERE token_hash = %s", (token_hash,))
        return None

    db.execute("UPDATE users SET verified = TRUE WHERE id = %s", (row["user_id"],))
    db.execute("DELETE FROM verification_tokens WHERE token_hash = %s", (token_hash,))
    return row["user_id"]


def resend_verification(email: str) -> None:
    """
    FR-2 alternate flow — the link expired or never arrived.

    Telling an anonymous visitor "no such account" would let them test which UNT
    addresses are registered here.
    """
    user = db.query_one(
        "SELECT id, email, verified FROM users WHERE email = %s", (email.lower(),)
    )
    if user is None or user["verified"]:
        return
    send_verification(user["id"], user["email"])
