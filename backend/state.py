"""Mutable runtime state.

Other modules read/write via attribute access:
    from backend import state
    state.ATTACK_MODEL = trained
    if state.ATTACK_MODEL is not None: ...

Do NOT use `from backend.state import X` for mutable values — that captures a snapshot.
"""

# ── Threat-level pipeline (loaded from .pkl files at startup) ──────────────
threat_model = None
threat_scaler = None
threat_le = None

# ── 5-class attack classifier (trained or restored from cache) ─────────────
ATTACK_MODEL = None
ATTACK_SCALER = None
ATTACK_LE = None

# ── Anomaly detector ───────────────────────────────────────────────────────
ISOLATION_MODEL = None
ISOLATION_SCALER = None

# ── Explainability ─────────────────────────────────────────────────────────
SHAP_EXPLAINER = None

# ── Derived data for dashboard widgets ─────────────────────────────────────
METRICS = {"error": "Not loaded yet"}
HEATMAP_DATA = None
SAMPLE_CONNECTIONS = None

# ── ARIA chatbot — per-session conversation history ────────────────────────
ARIA_CONVERSATIONS = {}
