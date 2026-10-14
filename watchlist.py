
from flask import Blueprint, jsonify, request

watchlist_bp = Blueprint("watchlist", __name__)

@watchlist_bp.route("/watchlist", methods=["GET"])
def get_watchlist():
    return jsonify({
        "message": "Watchlist feature is working",
        "items": []
    })
