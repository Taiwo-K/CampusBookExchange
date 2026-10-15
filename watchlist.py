
from flask import Blueprint, jsonify, request

watchlist_bp = Blueprint("watchlist", __name__)

@watchlist_bp.route("/watchlist", methods=["GET"])
def get_watchlist():
    return jsonify({
        "message": "Watchlist feature is working",
        "items": []
    })

@watchlist_bp.route("/watchlist", methods=["POST"])
def add_watchlist():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A JSON object is required"
        }), 400

    material_id = data.get("material_id")

    if type(material_id) is not int or material_id <= 0:
        return jsonify({
            "error": "A valid material_id is required"
        }), 400

    return jsonify({
        "message": "Watchlist request received",
        "material_id": material_id
    }), 200

@watchlist_bp.route("/watchlist/<int:material_id>", methods=["DELETE"])
def remove_watchlist(material_id):
    if material_id <= 0:
        return jsonify({
            "error": "A valid material_id is required"
        }), 400

    return jsonify({
        "message": "Watchlist removal request received",
        "material_id": material_id
    }), 200


