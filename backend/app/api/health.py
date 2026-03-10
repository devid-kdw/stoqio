"""Health-check endpoint for Phase 1 proxy verification."""

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health():
    """Return a simple health-check response.

    GET /api/v1/health → {"status": "ok"}
    """
    return jsonify({"status": "ok"}), 200
