"""Flask application factory.

Importing `create_app` and calling it builds a fully-wired app:
  1. Boots logging + config (via `backend.config`)
  2. Loads or trains all ML models
  3. Registers every blueprint
"""
import logging

import joblib
from flask import Flask
from flask_cors import CORS

# Importing config first runs load_dotenv() and configures logging.
from backend import state
from backend.config import (
    ALLOWED_ORIGINS,
    DATASET_PATH,
    FORCE_RETRAIN,
    LABEL_ENCODER_PATH,
    SCALER_PATH,
    THREAT_MODEL_PATH,
)
from backend.models import cache as model_cache
from backend.models.trainer import train_all_models
from backend.routes.aria import bp as aria_bp
from backend.routes.explain import bp as explain_bp
from backend.routes.meta import bp as meta_bp
from backend.routes.predict import bp as predict_bp
from backend.routes.reports import bp as reports_bp

logger = logging.getLogger("soc.app")


def _load_threat_pipeline():
    """Load the legacy threat-level RF, scaler, and label encoder from .pkl files."""
    state.threat_model = joblib.load(THREAT_MODEL_PATH)
    state.threat_scaler = joblib.load(SCALER_PATH)
    state.threat_le = joblib.load(LABEL_ENCODER_PATH)


def _ensure_models_ready():
    """Load model cache if available, otherwise train from the dataset."""
    try:
        if FORCE_RETRAIN or not model_cache.try_load(DATASET_PATH):
            train_all_models(DATASET_PATH)
            model_cache.save(DATASET_PATH)
    except Exception as e:
        logger.exception("ERROR loading metrics")
        state.METRICS = {"error": str(e)}


def create_app():
    """Build and return the Flask app."""
    app = Flask(__name__)
    CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=False)

    # Optional UBA blueprint — only loads if SQLAlchemy is installed.
    try:
        from backend.uba import setup_uba
        setup_uba(app)
    except ImportError as e:
        logger.warning("UBA module could not be loaded. Ensure sqlalchemy is installed. %s", e)

    _load_threat_pipeline()
    _ensure_models_ready()

    app.register_blueprint(predict_bp)
    app.register_blueprint(explain_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(aria_bp)
    app.register_blueprint(meta_bp)

    return app
