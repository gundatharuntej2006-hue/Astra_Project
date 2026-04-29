"""Gemini client wrapper. Single chokepoint for all LLM calls."""
import logging

from backend.config import GEMINI_API_KEY, GEMINI_MODEL_NAME

logger = logging.getLogger("soc.gemini")

CLIENT = None
AVAILABLE = False

try:
    from google import genai

    if GEMINI_API_KEY:
        CLIENT = genai.Client(api_key=GEMINI_API_KEY)
        AVAILABLE = True
        logger.info("Gemini ready (model=%s).", GEMINI_MODEL_NAME)
    else:
        logger.warning("GEMINI_API_KEY not found in .env. Falling back to templates.")
except ImportError:
    logger.warning("google-genai not installed.")


def generate(prompt):
    """Send a prompt to Gemini. Caller must check AVAILABLE first or handle exceptions."""
    response = CLIENT.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=prompt,
    )
    return response.text
