"""Incident report generation — Gemini-backed with template fallback."""
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from backend.services import gemini

logger = logging.getLogger("soc.reports")

bp = Blueprint("reports", __name__)

ACTION_TEMPLATES = {
    "DoS":    "RECOMMENDED ACTIONS: Implement rate limiting and DDoS mitigation.",
    "Probe":  "RECOMMENDED ACTIONS: Block source IP and conduct vulnerability scan.",
    "R2L":    "RECOMMENDED ACTIONS: Lock accounts and force password resets.",
    "U2R":    "RECOMMENDED ACTIONS: Isolate system and conduct forensic analysis.",
    "Normal": "STATUS: No immediate action required.",
}


@bp.route("/generate-report", methods=["POST"])
def generate_report():
    """Generate an incident report from prediction data."""
    try:
        data = request.get_json()
        threat = data.get("threat", "UNKNOWN")
        attack_type = data.get("attack_type", "Unknown")
        confidence = data.get("confidence", 0)
        shap_vals = data.get("shap_values", [])
        is_anomalous = data.get("is_anomalous", False)
        timestamp = data.get("timestamp", datetime.now().isoformat())

        top_features = shap_vals[:3] if shap_vals else []
        feature_text = ", ".join(
            f"{f['feature']} (contribution: {'+' if f['value'] > 0 else ''}{f['value']:.3f})"
            for f in top_features
        ) if top_features else "feature importance data not available"

        if attack_type == "Normal" and not is_anomalous:
            p1 = (f"INCIDENT REPORT — {timestamp}\n\n"
                  f"Analysis indicates NORMAL traffic patterns. Threat Level: {threat} ({confidence}%).")
        elif is_anomalous and attack_type == "Normal":
            p1 = (f"INCIDENT REPORT — {timestamp}\n\n"
                  f"ZERO-DAY ALERT: Anomaly detector flagged unusual patterns not matching known attack signatures.")
        else:
            p1 = (f"INCIDENT REPORT — {timestamp}\n\n"
                  f"ALERT: A {attack_type} attack has been detected with {confidence}% confidence.")

        p2 = f"The decision was driven primarily by these features: {feature_text}."
        p3 = ACTION_TEMPLATES.get(attack_type, ACTION_TEMPLATES["Normal"])
        template_report = f"{p1}\n\n{p2}\n\n{p3}"

        report = template_report
        if gemini.AVAILABLE:
            try:
                prompt = (
                    f"You are a professional SOC Analyst. Generate a concise, high-impact security incident report based on these AI results:\n"
                    f"- Threat Level: {threat}\n"
                    f"- Confidence: {confidence}%\n"
                    f"- Attack Type: {attack_type}\n"
                    f"- Zero-Day/Anomalous: {is_anomalous}\n"
                    f"- Key Features: {feature_text}\n\n"
                    f"Include: 1. Executive Summary, 2. Technical Analysis, 3. Priority Action Items. "
                    f"Format for terminal display, under 250 words."
                )
                report = gemini.generate(prompt)
            except Exception as gem_e:
                logger.error("Gemini error: %s", gem_e)
                report = template_report

        return jsonify({"success": True, "data": {"report": report}, "error": None})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "data": None}), 500
