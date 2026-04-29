"""Per-request inference helpers: SHAP explanation + anomaly detection.

The SHAP path is hot — `/predict` calls both compute_shap_values AND compute_shap_xai
on the same input. We memoize the underlying SHAP computation by the input fingerprint
so the second call (and any repeated identical predictions) is free.
"""
import hashlib
import logging
from collections import OrderedDict

from backend import state
from backend.constants import FEATURES

logger = logging.getLogger("soc.inference")

# Bounded cache: fingerprint(values) → (scaled, sv, atk_pred). LRU eviction at MAX entries.
_SHAP_CACHE = OrderedDict()
_SHAP_CACHE_MAX = 256


def _fingerprint(df_input):
    """Hash a 1-row DataFrame's values. ~5µs — much cheaper than a SHAP recompute."""
    return hashlib.md5(df_input.values.tobytes()).hexdigest()


def _shap_compute(df_input):
    """Run SHAP + scaler + predict once per unique input; serve from cache otherwise."""
    key = _fingerprint(df_input)
    if key in _SHAP_CACHE:
        _SHAP_CACHE.move_to_end(key)
        return _SHAP_CACHE[key]

    scaled = state.ATTACK_SCALER.transform(df_input)
    sv = state.SHAP_EXPLAINER.shap_values(scaled)
    atk_pred = state.ATTACK_MODEL.predict(scaled)[0]
    result = (scaled, sv, atk_pred)

    _SHAP_CACHE[key] = result
    if len(_SHAP_CACHE) > _SHAP_CACHE_MAX:
        _SHAP_CACHE.popitem(last=False)
    return result


def build_human_label(feature, direction, pct, raw_val):
    """Plain-English description of a single SHAP contribution."""
    dir_word = "increased" if direction == "increases_risk" else "decreased"
    formatted_feature = feature.replace("_", " ").title()
    formatted_val = f"{raw_val:,.2f}" if abs(raw_val) >= 1000 else str(round(raw_val, 4))
    return f"{formatted_feature} (={formatted_val}) {dir_word} risk by {pct}%"


def _select_class_shap(sv, pred_class_index):
    """Extract per-feature SHAP for the predicted class — handles list/array/3D shapes."""
    if isinstance(sv, list):
        return sv[pred_class_index][0]
    # XGBoost SHAP returns a 3D array (n_samples, n_classes, n_features) for multiclass;
    # sklearn returns 2D (n_samples, n_features) when given a single sample. Disambiguate.
    if sv.ndim == 3:
        return sv[0, pred_class_index]
    return sv[0]


def compute_shap_values(df_input):
    """Legacy SHAP format: top-15 contributions, sorted by absolute value."""
    if state.SHAP_EXPLAINER is None or state.ATTACK_SCALER is None:
        return None
    try:
        _, sv, atk_pred = _shap_compute(df_input)
        values = _select_class_shap(sv, int(atk_pred))
        contributions = [
            {"feature": fname, "value": round(float(values[i]), 4)}
            for i, fname in enumerate(FEATURES)
        ]
        contributions.sort(key=lambda x: abs(x["value"]), reverse=True)
        return contributions[:15]
    except Exception as e:
        logger.error("SHAP error: %s", e)
        return None


def compute_shap_xai(df_input):
    """Full XAI payload: top-3 reasons, top-10 contributions, directions, percentages."""
    if (
        state.SHAP_EXPLAINER is None
        or state.ATTACK_SCALER is None
        or state.ATTACK_MODEL is None
        or state.ATTACK_LE is None
    ):
        return None
    try:
        scaled, sv, atk_pred = _shap_compute(df_input)
        atk_type = state.ATTACK_LE.inverse_transform([atk_pred])[0]
        class_labels = state.ATTACK_LE.classes_.tolist()
        pred_class_index = class_labels.index(atk_type)

        shap_for_pred = _select_class_shap(sv, pred_class_index)

        input_array = df_input.values
        contributions = []
        for i, fname in enumerate(FEATURES):
            sv_val = float(shap_for_pred[i])
            contributions.append({
                "feature":    fname,
                "value":      float(scaled[0][i]),
                "raw_value":  float(input_array[0][i]),
                "shap_value": round(sv_val, 4),
                "abs_shap":   round(abs(sv_val), 4),
                "direction":  "increases_risk" if sv_val > 0 else "decreases_risk",
            })

        contributions.sort(key=lambda x: x["abs_shap"], reverse=True)
        top_contributions = contributions[:10]

        total_abs = sum(c["abs_shap"] for c in top_contributions) or 1.0
        for c in top_contributions:
            c["pct"] = round((c["abs_shap"] / total_abs) * 100, 1)

        top3_reasons = [
            build_human_label(c["feature"], c["direction"], c["pct"], c["raw_value"])
            for c in top_contributions[:3]
        ]

        return {
            "top3_reasons":      top3_reasons,
            "top_contributions": top_contributions,
            "predicted_class":   atk_type,
            "class_labels":      class_labels,
        }
    except Exception as e:
        logger.error("[XAI] SHAP computation failed: %s", e)
        return None


def reset_shap_cache():
    """Clear the SHAP cache. Call after retraining the attack classifier."""
    _SHAP_CACHE.clear()


def check_anomaly(df_input):
    """Run Isolation Forest on a single input. Returns (is_anomaly, score)."""
    if state.ISOLATION_MODEL is None or state.ISOLATION_SCALER is None:
        return False, 0.0
    try:
        scaled = state.ISOLATION_SCALER.transform(df_input)
        pred = state.ISOLATION_MODEL.predict(scaled)[0]
        score = float(state.ISOLATION_MODEL.score_samples(scaled)[0])
        return bool(pred == -1), round(score, 4)
    except Exception as e:
        logger.error("Anomaly detection error: %s", e)
        return False, 0.0
