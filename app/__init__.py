"""

`create_app()` builds and returns the Flask app. Nothing runs at import
time, which is what lets the tests build a fresh app per test run.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify

from app import db


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-not-for-production")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # Caps the whole request body (5 photos x 5 MB + form fields) at the transport layer.
    app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

    # ---- Health check -----------------------------------------------
    @app.get("/api/health")
    def health():
        try:
            row = db.query_one("SELECT COUNT(*) AS n FROM courses")
            return jsonify(ok=True, database="connected", courses=row["n"])
        except Exception as exc:                      # noqa: BLE001
            # Return the reason rather than a blank 500 — when this
            # fails it is almost always DATABASE_URL.
            return jsonify(ok=False, database="unreachable", error=str(exc)), 503

    # ---- Feature blueprints -----------------------------------------
    # One file per feature area, matching the task split. Register new
    # ones here as they are built.
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.search import bp as search_bp
    from app.blueprints.verify import bp as verify_bp
    from app.blueprints.listings import bp as listings_bp
    from app.blueprints.messages import bp as message_bp


    app.register_blueprint(auth_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(verify_bp)
    app.register_blueprint(listings_bp)
    app.register_blueprint(message_bp)

    # Makes the signed-in user (or None) available to every template as
    # `current_user`, so base.html can show the logout control without
    # every route having to pass it in by hand. Looked up through the
    # module (like app.db elsewhere) rather than a bound import, so
    # tests can monkeypatch app.auth.current_user.
    from app import auth
    app.context_processor(lambda: {"current_user": auth.current_user()})

    # FR-2 safety net — blocks unverified accounts from every blueprint
    # not on the public allowlist, even one that forgets
    # @require_verified.
    auth.register_verification_guard(app)

    # from app.blueprints.watchlist import bp as watchlist_bp # FR-12, FR-13
    # from app.blueprints.budget    import bp as budget_bp    # FR-14..FR-17

    return app
