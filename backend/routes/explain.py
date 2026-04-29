"""SHAP-only endpoint — fetch an explanation without re-running the prediction."""
import pandas as pd
from flask import Blueprint, jsonify, request

from backend.constants import FEATURES
from backend.models.inference import compute_shap_xai

bp = Blueprint("explain", __name__)


@bp.route("/explain", methods=["POST"])
def explain():
    """Same input as /predict, but returns only the XAI payload."""
    try:
        data = request.get_json()
        row = {f: data.get(f, 0) for f in FEATURES}
        df_input = pd.DataFrame([row])

        xai_payload = compute_shap_xai(df_input)
        if xai_payload is None:
            return jsonify({"xai": None, "error": "SHAP explainer not available"}), 200

        return jsonify({"xai": xai_payload})
    except Exception as e:
        return jsonify({"error": str(e), "xai": None}), 500
