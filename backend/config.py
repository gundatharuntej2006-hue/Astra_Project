"""Centralized config — env vars + logging setup.

Importing this module is the side-effecting step that:
  1. Loads .env via python-dotenv
  2. Configures the root logger
"""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("soc")

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "KDDTrain+.txt")
THREAT_MODEL_PATH = os.path.join(BASE_DIR, "threat_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "scaler.pkl")
LABEL_ENCODER_PATH = os.path.join(BASE_DIR, "label_encoder.pkl")
MODEL_CACHE_PATH = os.path.join(BASE_DIR, "models_cache.pkl")

# ── HTTP server ────────────────────────────────────────────────────────────
PORT = int(os.getenv("PORT", "5000"))
HOST = os.getenv("HOST", "127.0.0.1")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "").lower() in ("1", "true", "yes")

_default_origins = (
    "http://localhost:5173,http://localhost:5174,"
    "http://127.0.0.1:5173,http://127.0.0.1:5174"
)
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",")
    if o.strip()
]

# ── External services ──────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
IPSTACK_API_KEY = os.getenv("IPSTACK_API_KEY")

# ── Behavior flags ─────────────────────────────────────────────────────────
FORCE_RETRAIN = os.getenv("RETRAIN_MODELS", "").lower() in ("1", "true", "yes")
