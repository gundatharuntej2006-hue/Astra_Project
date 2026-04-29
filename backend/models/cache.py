"""Persist trained model state across boots so restart is fast.

Cache invalidates automatically when the dataset changes (size+mtime fingerprint)
or the cache schema bumps (CACHE_VERSION).
"""
import logging
import os

import joblib

from backend import state
from backend.config import MODEL_CACHE_PATH
from backend.models.inference import reset_shap_cache
from backend.models.trainer import SHAP_AVAILABLE

logger = logging.getLogger("soc.cache")

CACHE_VERSION = 5  # bump when train_all_models output schema changes (v5: smaller RFs for 512MB free tier)


def _dataset_fingerprint(file_path):
    """Cheap fingerprint: size + mtime. Avoids hashing 19MB on every boot."""
    st = os.stat(file_path)
    return f"{st.st_size}:{int(st.st_mtime)}"


def save(file_path):
    """Persist trained models + derived data so the next boot skips training."""
    try:
        payload = {
            "version":            CACHE_VERSION,
            "fingerprint":        _dataset_fingerprint(file_path),
            "metrics":            state.METRICS,
            "attack_model":       state.ATTACK_MODEL,
            "attack_scaler":      state.ATTACK_SCALER,
            "attack_le":          state.ATTACK_LE,
            "isolation_model":    state.ISOLATION_MODEL,
            "isolation_scaler":   state.ISOLATION_SCALER,
            "heatmap_data":       state.HEATMAP_DATA,
            "sample_connections": state.SAMPLE_CONNECTIONS,
        }
        joblib.dump(payload, MODEL_CACHE_PATH, compress=3)
        logger.info("Model cache saved → %s", MODEL_CACHE_PATH)
    except Exception as e:
        logger.error("Failed to save model cache: %s", e)


def try_load(file_path):
    """Attempt to restore trained state from disk. Returns True on success."""
    if not os.path.exists(MODEL_CACHE_PATH):
        return False
    try:
        payload = joblib.load(MODEL_CACHE_PATH)
        if payload.get("version") != CACHE_VERSION:
            logger.info("Model cache version mismatch — will retrain.")
            return False
        if payload.get("fingerprint") != _dataset_fingerprint(file_path):
            logger.info("Dataset fingerprint changed — will retrain.")
            return False

        state.METRICS            = payload["metrics"]
        state.ATTACK_MODEL       = payload["attack_model"]
        state.ATTACK_SCALER      = payload["attack_scaler"]
        state.ATTACK_LE          = payload["attack_le"]
        state.ISOLATION_MODEL    = payload["isolation_model"]
        state.ISOLATION_SCALER   = payload["isolation_scaler"]
        state.HEATMAP_DATA       = payload["heatmap_data"]
        state.SAMPLE_CONNECTIONS = payload["sample_connections"]

        # SHAP explainer is cheap to rebuild (sub-second) and pickling it is brittle.
        if SHAP_AVAILABLE and state.ATTACK_MODEL is not None:
            try:
                import shap
                state.SHAP_EXPLAINER = shap.TreeExplainer(state.ATTACK_MODEL)
            except Exception as e:
                logger.error("SHAP rebuild failed: %s", e)
                state.SHAP_EXPLAINER = None

        reset_shap_cache()  # Per-input cache from a prior process is meaningless.
        logger.info("Model cache loaded — skipping retrain.")
        return True
    except Exception as e:
        logger.warning("Could not load model cache (%s) — will retrain.", e)
        return False
