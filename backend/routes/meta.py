"""Dashboard data + admin endpoints: metrics, heatmap, samples, dataset upload, health."""
import logging
import os

from flask import Blueprint, jsonify, request

from backend import state
from backend.config import DATASET_PATH, IPSTACK_API_KEY
from backend.models import cache as model_cache
from backend.models.trainer import SHAP_AVAILABLE, train_all_models
from backend.services import gemini

logger = logging.getLogger("soc.meta")

bp = Blueprint("meta", __name__)


@bp.route("/heatmap-data", methods=["GET"])
def heatmap_data():
    """Return protocol×service attack frequency data."""
    if state.HEATMAP_DATA is None:
        return jsonify({"success": False, "error": "Heatmap data not available", "data": None}), 500
    return jsonify({"success": True, "data": state.HEATMAP_DATA, "error": None})


@bp.route("/sample-connections", methods=["GET"])
def sample_connections():
    """Return 20 sample connections for simulation mode."""
    if state.SAMPLE_CONNECTIONS is None:
        return jsonify({"success": False, "error": "Sample data not available", "data": None}), 500
    return jsonify({"success": True, "data": state.SAMPLE_CONNECTIONS, "error": None})


@bp.route("/model-metrics", methods=["GET"])
def model_metrics():
    if "error" in state.METRICS:
        return jsonify(state.METRICS), 500
    return jsonify(state.METRICS)


@bp.route("/upload-dataset", methods=["POST"])
def upload_dataset():
    """Upload KDDTrain+.txt and retrain models."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        file.save(DATASET_PATH)
        logger.info("Dataset uploaded and saved to: %s", DATASET_PATH)

        train_all_models(DATASET_PATH)
        model_cache.save(DATASET_PATH)

        return jsonify({
            "status":  "success",
            "message": "Dataset uploaded and models retrained successfully",
            "metrics": state.METRICS,
        })
    except Exception as e:
        logger.exception("Upload error: %s", e)
        return jsonify({"error": str(e)}), 500


@bp.route("/api-status", methods=["GET"])
def api_status():
    """Live status of all integrated APIs and services."""
    status = {
        "gemini":            gemini.AVAILABLE,
        "ipstack":           bool(IPSTACK_API_KEY),
        "shap":              SHAP_AVAILABLE and state.SHAP_EXPLAINER is not None,
        "aria":              gemini.AVAILABLE,
        "attack_classifier": state.ATTACK_MODEL is not None,
        "isolation_forest":  state.ISOLATION_MODEL is not None,
    }
    return jsonify({"success": True, "data": status, "error": None})


@bp.route("/health", methods=["GET"])
def health():
    """Deep health check — reports liveness AND readiness of each subsystem."""
    checks = {
        "threat_model_loaded":  state.threat_model is not None,
        "scaler_loaded":        state.threat_scaler is not None,
        "label_encoder_loaded": state.threat_le is not None,
        "attack_classifier":    state.ATTACK_MODEL is not None,
        "isolation_forest":     state.ISOLATION_MODEL is not None,
        "shap_explainer":       state.SHAP_EXPLAINER is not None,
        "gemini":               gemini.AVAILABLE,
        "ipstack":              bool(IPSTACK_API_KEY),
        "metrics_available":    "error" not in state.METRICS,
    }
    ready = all([
        checks["threat_model_loaded"],
        checks["scaler_loaded"],
        checks["label_encoder_loaded"],
        checks["attack_classifier"],
    ])
    status_code = 200 if ready else 503
    return jsonify({
        "status": "online" if ready else "degraded",
        "ready":  ready,
        "checks": checks,
    }), status_code
