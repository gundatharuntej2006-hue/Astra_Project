"""ARIA chatbot endpoints — conversational SOC assistant."""
import logging

from flask import Blueprint, jsonify, request

from backend import state
from backend.services import gemini
from backend.services.aria import ARIA_SYSTEM_PROMPT, keyword_fallback

logger = logging.getLogger("soc.aria")

bp = Blueprint("aria", __name__)

MAX_HISTORY = 20


@bp.route("/aria-chat", methods=["POST"])
def aria_chat():
    """Cybersecurity-focused AI assistant."""
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        session_id = data.get("session_id", "default")
        dashboard_context = data.get("dashboard_context", None)

        if not user_message:
            return jsonify({"success": False, "error": "Empty message", "data": None}), 400

        history = state.ARIA_CONVERSATIONS.setdefault(session_id, [])
        history.append({"role": "user", "content": user_message})
        if len(history) > MAX_HISTORY:
            del history[:-MAX_HISTORY]

        if gemini.AVAILABLE:
            try:
                context_block = ""
                if dashboard_context:
                    context_block = "\n\n[CURRENT DASHBOARD STATE]\n"
                    if dashboard_context.get("lastThreat"):
                        context_block += f"- Last detected threat level: {dashboard_context['lastThreat']}\n"
                    if dashboard_context.get("lastAttackType"):
                        context_block += f"- Last attack type: {dashboard_context['lastAttackType']}\n"
                    if dashboard_context.get("lastConfidence"):
                        context_block += f"- Confidence: {dashboard_context['lastConfidence']}%\n"
                    if dashboard_context.get("isAnomalous"):
                        context_block += "- Zero-Day anomaly detected: YES\n"
                    if dashboard_context.get("shapValues"):
                        top3 = dashboard_context["shapValues"][:3]
                        shap_text = ", ".join(f"{s['feature']}={s['value']}" for s in top3)
                        context_block += f"- Top SHAP features: {shap_text}\n"

                history_text = ""
                for msg in history[:-1]:
                    role_label = "Analyst" if msg["role"] == "user" else "ARIA"
                    history_text += f"{role_label}: {msg['content']}\n"

                full_prompt = (
                    f"{ARIA_SYSTEM_PROMPT}"
                    f"{context_block}\n\n"
                    f"[CONVERSATION HISTORY]\n{history_text}\n"
                    f"Analyst: {user_message}\n\n"
                    f"ARIA:"
                )

                reply = gemini.generate(full_prompt).strip()
            except Exception as gem_e:
                logger.error("ARIA Gemini error: %s", gem_e)
                reply = "I'm experiencing a temporary connection issue with my AI engine. Please try again in a moment, or check that the Gemini API key is configured correctly."
        else:
            reply = keyword_fallback(user_message)

        history.append({"role": "assistant", "content": reply})

        return jsonify({
            "success": True,
            "data": {"reply": reply, "session_id": session_id},
            "error": None,
        })
    except Exception as e:
        logger.exception("ARIA chat error: %s", e)
        return jsonify({"success": False, "error": str(e), "data": None}), 500


@bp.route("/aria-clear", methods=["POST"])
def aria_clear():
    """Clear ARIA conversation history for a session."""
    try:
        data = request.get_json()
        session_id = data.get("session_id", "default")
        state.ARIA_CONVERSATIONS.pop(session_id, None)
        return jsonify({"success": True, "data": None, "error": None})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "data": None}), 500
