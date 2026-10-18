"""
Application factory.

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

    # ---- Health check -----------------------------------------------
    # The smallest thing that proves all three tiers are talking to each
    # other. Sprint 0 is not finished until this returns ok on the
    # deployed site, not just on localhost.
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

    app.register_blueprint(auth_bp)
    app.register_blueprint(search_bp)

    # Temporary: lets everyone build features before FR-3 login exists.
    # Only active when DEV_LOGIN_AS is set and debug mode is on.
    from app.auth import dev_login_if_enabled

    dev_login_if_enabled(app)

    # from app.blueprints.listings import bp as listings_bp   # FR-4..FR-7
    # from app.blueprints.messages  import bp as messages_bp  # FR-11
    # from app.blueprints.watchlist import bp as watchlist_bp # FR-12, FR-13
    # from app.blueprints.budget    import bp as budget_bp    # FR-14..FR-17

    return app
