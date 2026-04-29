# Project Structure & Reference Guide

Complete walkthrough of the codebase: every file, every module, every function. Read this end-to-end and you should be able to find anything in 30 seconds.

---

## Top-level layout

```
ai-threat-detection-soc/
├── backend/                    # Python package — Flask backend (NEW: refactored from monolith)
│   ├── __init__.py
│   ├── app.py                  # Flask app factory
│   ├── config.py               # Env vars + logging setup
│   ├── constants.py            # FEATURES, label maps, attack categories
│   ├── state.py                # Shared mutable runtime state
│   ├── uba.py                  # User Behavior Analytics blueprint
│   ├── models/
│   │   ├── trainer.py          # Train all ML models from dataset
│   │   ├── cache.py            # Save/load model cache
│   │   └── inference.py        # SHAP + anomaly helpers (with LRU cache)
│   ├── services/
│   │   ├── gemini.py           # Gemini LLM wrapper
│   │   ├── geo.py              # IPStack geolocation
│   │   └── aria.py             # ARIA system prompt + offline fallback
│   └── routes/
│       ├── predict.py          # POST /predict, /predict-batch
│       ├── explain.py          # POST /explain
│       ├── reports.py          # POST /generate-report
│       ├── aria.py             # POST /aria-chat, /aria-clear
│       └── meta.py             # /heatmap-data, /sample-connections,
│                               #   /model-metrics, /upload-dataset,
│                               #   /api-status, /health
├── frontend/                   # React + Vite + TypeScript dashboard
│   ├── src/
│   │   ├── api/                # API client modules (threatApi, ariaApi, ubaApi)
│   │   ├── app/                # Top-level App.tsx + components
│   │   │   ├── App.tsx
│   │   │   ├── components/     # 30+ React components
│   │   │   └── context/
│   │   ├── hooks/              # Custom hooks (useThreatPredict, useAudioAlert)
│   │   ├── styles/
│   │   └── main.tsx
│   ├── package.json
│   ├── pnpm-lock.yaml
│   └── vite.config.ts
├── backend_final.py            # Thin entry point (12 lines) — calls create_app()
├── train_model.py              # Standalone script to train threat-level model → .pkl
├── download_dataset.py         # Downloads NSL-KDD dataset
├── qr.py                       # QR code generator (for mobile access)
├── test_backend.py             # Tiny smoke test
├── requirements.txt            # NEW — pinned Python deps
├── KDDTrain+.txt               # Dataset (gitignored, ~19 MB)
├── threat_model.pkl            # Trained threat-level model (gitignored)
├── scaler.pkl                  # StandardScaler (gitignored)
├── label_encoder.pkl           # LabelEncoder (gitignored)
├── models_cache.pkl            # NEW — Cached attack/iso/heatmap state (gitignored)
├── uba_logs.db                 # SQLite UBA database (gitignored)
├── start_backend.bat           # Windows launcher for backend
├── start_backend.ps1           # PowerShell launcher for backend
├── start_frontend.bat          # Windows launcher for frontend
├── start_frontend.ps1          # PowerShell launcher for frontend
├── .env                        # Secrets (gitignored — must be created locally)
├── .gitignore                  # NEW — hardened
├── README.md                   # Original project README
├── SETUP_COMPLETE.md           # Setup notes from original
├── CHANGES.md                  # NEW — what changed in this session
└── STRUCTURE.md                # NEW — this file
```

---

## Quick start

### Prerequisites
- Python 3.10+ (tested on 3.13)
- Node.js 20+ with `pnpm`
- ~500 MB disk for dependencies

### Setup
```bash
# Backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python download_dataset.py      # Fetches KDDTrain+.txt if missing
python train_model.py           # Generates the 3 .pkl files

# Frontend
cd frontend
pnpm install
```

### Run
```bash
# Terminal 1 — backend
python backend_final.py         # http://localhost:5000

# Terminal 2 — frontend
cd frontend && pnpm dev         # http://localhost:5173 (or 5174)
```

Or just double-click `start_backend.bat` and `start_frontend.bat` on Windows.

### Optional: create a `.env` file
```
GEMINI_API_KEY=your-gemini-key
IPSTACK_API_KEY=your-ipstack-key
LOG_LEVEL=INFO
```

Without these, the dashboard still works — Gemini falls back to template reports, geolocation is disabled.

---

## Backend module reference

### `backend/app.py` — Flask app factory (62 lines)

The single entry point that wires everything together.

| Function | Purpose |
|---|---|
| `_load_threat_pipeline()` | Loads `threat_model.pkl`, `scaler.pkl`, `label_encoder.pkl` from disk into `state` |
| `_ensure_models_ready()` | Loads cache or trains all models from `KDDTrain+.txt` |
| `create_app()` | Builds the Flask app: registers CORS, UBA blueprint, all routes, returns app |

**Boot order:**
1. Import `backend.config` → loads `.env`, configures logging
2. Build Flask app + CORS
3. Register UBA blueprint (if SQLAlchemy installed)
4. Load threat pipeline `.pkl` files
5. Load model cache OR train models
6. Register all 5 route blueprints

---

### `backend/config.py` — Configuration

Reads environment variables once at import time. All paths are absolute.

| Constant | Default | Source |
|---|---|---|
| `BASE_DIR` | parent of `backend/` | computed |
| `DATASET_PATH` | `BASE_DIR/KDDTrain+.txt` | computed |
| `THREAT_MODEL_PATH` | `BASE_DIR/threat_model.pkl` | computed |
| `SCALER_PATH` | `BASE_DIR/scaler.pkl` | computed |
| `LABEL_ENCODER_PATH` | `BASE_DIR/label_encoder.pkl` | computed |
| `MODEL_CACHE_PATH` | `BASE_DIR/models_cache.pkl` | computed |
| `PORT` | 5000 | env `PORT` |
| `HOST` | 127.0.0.1 | env `HOST` |
| `FLASK_DEBUG` | False | env `FLASK_DEBUG` |
| `ALLOWED_ORIGINS` | local Vite ports | env `ALLOWED_ORIGINS` |
| `GEMINI_API_KEY` | None | env `GEMINI_API_KEY` |
| `GEMINI_MODEL_NAME` | `gemini-2.5-flash` | env `GEMINI_MODEL` |
| `IPSTACK_API_KEY` | None | env `IPSTACK_API_KEY` |
| `FORCE_RETRAIN` | False | env `RETRAIN_MODELS` |

Also configures the root logger format: `2026-04-28 19:30:01 [INFO] soc.app: message`.

---

### `backend/constants.py` — Pure data, no I/O

Static lookup tables shared across modules.

| Constant | Type | Description |
|---|---|---|
| `FEATURES` | `list[str]` | The 41 NSL-KDD feature names |
| `DATASET_COLUMNS` | `list[str]` | `FEATURES + ["label", "difficulty"]` |
| `REGION_IPS` | `dict` | Mock IP ranges per attack type for demo geolocation |
| `DOS_ATTACKS` | `set[str]` | Labels mapped to "DoS" category |
| `PROBE_ATTACKS` | `set[str]` | Labels mapped to "Probe" category |
| `R2L_ATTACKS` | `set[str]` | Labels mapped to "R2L" category |
| `U2R_ATTACKS` | `set[str]` | Labels mapped to "U2R" category |
| `HIGH_THREAT_LABELS` | `set[str]` | Labels classified as HIGH threat |

| Function | Returns |
|---|---|
| `map_attack_category(label)` | `"Normal" | "DoS" | "Probe" | "R2L" | "U2R"` |
| `map_threat(label)` | `"LOW" | "MEDIUM" | "HIGH"` |

---

### `backend/state.py` — Shared runtime state

Module-level mutable globals. Accessed via `from backend import state` then `state.X`.

| Variable | Type | Set by |
|---|---|---|
| `threat_model` | RandomForestClassifier | `app._load_threat_pipeline` |
| `threat_scaler` | StandardScaler | `app._load_threat_pipeline` |
| `threat_le` | LabelEncoder | `app._load_threat_pipeline` |
| `ATTACK_MODEL` | RandomForestClassifier | `trainer` or `cache` |
| `ATTACK_SCALER` | StandardScaler | `trainer` or `cache` |
| `ATTACK_LE` | LabelEncoder | `trainer` or `cache` |
| `ISOLATION_MODEL` | IsolationForest | `trainer` or `cache` |
| `ISOLATION_SCALER` | StandardScaler | `trainer` or `cache` |
| `SHAP_EXPLAINER` | shap.TreeExplainer | `trainer` or `cache` |
| `METRICS` | dict | `trainer` or `cache` |
| `HEATMAP_DATA` | dict | `trainer` or `cache` |
| `SAMPLE_CONNECTIONS` | list | `trainer` or `cache` |
| `ARIA_CONVERSATIONS` | dict[session_id, history] | `routes.aria` |

---

### `backend/uba.py` — User Behavior Analytics

SQLAlchemy-backed blueprint at `/api/uba/*`. Per-user Isolation Forest with risk scoring.

**Database models:**
- `UserActivity` — every login/download/etc. with anomaly score
- `UserRisk` — aggregated per-user risk score (smoothed, decays over time)

**Helpers:**
| Function | Purpose |
|---|---|
| `get_db()` | Yields a SQLAlchemy session (used as generator) |
| `extract_features(activity)` | `[hour, data_mb, duration, failed_login]` |
| `train_user_baseline(db, user_id)` | Fits IsolationForest if user has ≥10 activities |
| `detect_anomaly(db, user_id, activity)` | `(is_anomalous, score 0-100)` |
| `update_user_risk(db, user_id, score)` | Smoothed update: 70% old + 30% new |

**Routes:**
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/uba/track` | `{user_id, action, ip_address, ...}` | activity_id, is_anomalous, risk |
| GET | `/api/uba/dashboard` | — | recent_activities, risk_scores, alerts |
| POST | `/api/uba/simulate` | `{scenario, user_id}` | demo scenario results |

`scenario` ∈ `"3am_login"`, `"large_download"`, `"new_country"`, `"brute_force"`, `"normal"`.

---

### `backend/models/trainer.py` — Training pipeline

| Function | Purpose |
|---|---|
| `train_all_models(file_path)` | Trains RF threat-level + LR threat-level + RF 5-class attack + Isolation Forest + creates SHAP explainer + builds heatmap + samples connections |

**Training stages (writes into `state`):**
1. **Threat-level RF + LR** — for the model-comparison view (`state.METRICS`)
2. **5-class attack classifier** — Normal/DoS/Probe/R2L/U2R (`state.ATTACK_MODEL`)
3. **Isolation Forest** — anomaly detector for zero-days (`state.ISOLATION_MODEL`)
4. **SHAP TreeExplainer** — built from the attack classifier (`state.SHAP_EXPLAINER`)
5. **Heatmap data** — protocol×service attack frequency (`state.HEATMAP_DATA`)
6. **Sample connections** — 4 examples per category for the simulation runner (`state.SAMPLE_CONNECTIONS`)

All RandomForests/IsolationForests use `n_jobs=2` (bounded — keeps machine responsive).

---

### `backend/models/cache.py` — Persistence

Saves trained model state to disk so subsequent boots skip retraining.

| Function | Purpose |
|---|---|
| `_dataset_fingerprint(file_path)` | `f"{size}:{int(mtime)}"` — used to invalidate when dataset changes |
| `save(file_path)` | Pickles state to `models_cache.pkl` |
| `try_load(file_path)` | Restores from cache. Returns `True` on success, `False` to trigger retrain |

**Cache invalidates when:**
- File doesn't exist
- `CACHE_VERSION` (currently 4) doesn't match
- Dataset size or mtime changed
- Pickle is corrupt

---

### `backend/models/inference.py` — Per-request helpers

| Function | Purpose |
|---|---|
| `_fingerprint(df_input)` | MD5 of input values — cache key |
| `_shap_compute(df_input)` | Computes SHAP values once per unique input, memoizes |
| `_select_class_shap(sv, idx)` | Extracts per-feature SHAP for the predicted class |
| `build_human_label(...)` | Plain-English description of one SHAP contribution |
| `compute_shap_values(df)` | Legacy format — top-15 contributions sorted by magnitude |
| `compute_shap_xai(df)` | Full XAI payload — top-3 reasons + top-10 contributions + percentages |
| `check_anomaly(df)` | Isolation Forest prediction → `(is_anomaly, score)` |
| `reset_shap_cache()` | Clear the LRU cache (called on retrain) |

**SHAP cache:** OrderedDict, 256-entry LRU, MD5-keyed. Cuts double computation per `/predict` call.

---

### `backend/services/gemini.py` — LLM wrapper

| Symbol | Purpose |
|---|---|
| `CLIENT` | `google.genai.Client` instance (or `None` if no API key) |
| `AVAILABLE` | Boolean: is Gemini ready? |
| `generate(prompt)` | Single chokepoint for all LLM calls — returns `response.text` |

Uses `gemini-2.5-flash` by default. Override with `GEMINI_MODEL` env var.

---

### `backend/services/geo.py` — Geolocation

| Function | Purpose |
|---|---|
| `geolocate_attack(attack_type)` | Returns `{lat, lng, city, country, ip}` or `None` |

Uses an internal `_GEO_CACHE` to avoid burning IPStack credits on repeated identical lookups. Adds tiny lat/lng jitter on cache hits so map markers don't stack.

---

### `backend/services/aria.py` — ARIA chatbot logic

| Symbol | Purpose |
|---|---|
| `ARIA_SYSTEM_PROMPT` | Multi-paragraph system prompt defining ARIA's identity, scope, attack class knowledge, response rules |
| `keyword_fallback(user_message)` | Offline canned responses when Gemini is unavailable. Matches on DoS/Probe/R2L/U2R/Zero-Day/SHAP/UBA/hello |

---

### `backend/routes/predict.py` — Prediction endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/predict` | Single-input prediction with full XAI + geolocation + anomaly score |
| POST | `/predict-batch` | CSV upload, batch predictions with attack/threat breakdowns |

`/predict` response shape:
```json
{
  "threat": "LOW|MEDIUM|HIGH",
  "confidence": 90.0,
  "probabilities": {"HIGH": 3.33, "LOW": 90.0, "MEDIUM": 6.67},
  "attack_type": "Normal|DoS|Probe|R2L|U2R",
  "attack_probabilities": {...},
  "shap_values": [...],
  "xai": {"top3_reasons": [...], "top_contributions": [...], ...},
  "is_anomalous": false,
  "anomaly_score": -0.4654,
  "location": {"lat": 0, "lng": 0, "city": "...", "country": "...", "ip": "..."}
}
```

---

### `backend/routes/explain.py` — XAI without re-predicting

| Method | Path | Description |
|---|---|---|
| POST | `/explain` | Same input as /predict, returns only `{xai: ...}` |

Used to load explanations for historical alerts.

---

### `backend/routes/reports.py` — Incident reports

| Method | Path | Description |
|---|---|---|
| POST | `/generate-report` | Gemini-backed incident report with template fallback |

Falls back to a 3-paragraph template when Gemini is unavailable.

---

### `backend/routes/aria.py` — ARIA chatbot

| Method | Path | Description |
|---|---|---|
| POST | `/aria-chat` | Chat with ARIA. Body: `{message, session_id, dashboard_context}`. Conversation history stored per session_id (max 20 messages). |
| POST | `/aria-clear` | Clear a session's history |

---

### `backend/routes/meta.py` — Dashboard data + admin

| Method | Path | Description |
|---|---|---|
| GET | `/heatmap-data` | Protocol×service attack frequency |
| GET | `/sample-connections` | 20 sample inputs (4 per category) for the simulation runner |
| GET | `/model-metrics` | Accuracy + confusion matrices for RF, LR, attack classifier |
| POST | `/upload-dataset` | Upload a new `KDDTrain+.txt`, retrain all models |
| GET | `/api-status` | Live status of integrated services |
| GET | `/health` | Deep readiness check (returns 503 when degraded) |

---

## Frontend reference

### Tech stack
- **React 18.3** + TypeScript
- **Vite 6.3.5** (dev server + build tool)
- **Tailwind CSS 4.1.12** + **Radix UI** primitives + **Material UI**
- **Recharts** + **D3** for visualizations
- **framer-motion** for animations
- **Lucide React** for icons

### Key components

| File | Purpose |
|---|---|
| `App.tsx` | Top-level state + tab routing (single/batch/uba) |
| `MatrixRain.tsx` | Background animation |
| `RadarSweep.tsx` | Animated threat radar (SVG) |
| `TerminalLog.tsx` | Live "monitor" log feed |
| `ThreatLevelDisplay.tsx` | Big LOW/MEDIUM/HIGH gauge with confidence |
| `AnalyticsPanel.tsx` | SHAP waterfall + probability breakdown |
| `ModelComparison.tsx` | RF vs LR confusion matrices |
| `ControlPanel.tsx` | Manual feature input form |
| `BatchAnalysis.tsx` | CSV upload + batch results |
| `AttackHeatmap.tsx` | Protocol×service heatmap |
| `AttackWorldMap.tsx` | D3 world map with attack origin markers |
| `NetworkGraph.tsx` | Force-directed attack flow viz |
| `UbaDashboard.tsx` | UBA monitoring tab |
| `AriaChatbot.tsx` | ARIA chat widget (bottom-right) |
| `XAIExplanationPanel.tsx` | Detailed SHAP explanation panel |
| `SimulationRunner.tsx` | "Run sample attack" button |
| `IncidentReport.tsx` | Gemini-generated executive report viewer |
| `PredictionHistory.tsx` | Last 100 predictions log |
| `SocMode.tsx` | Compact "war room" layout toggle |
| `DriftWarning.tsx` | Banner for model drift detection |
| `ZeroDayBadge.tsx` | Pulse badge for anomalous predictions |

### API client modules

| File | Purpose |
|---|---|
| `src/api/threatApi.ts` | `predictThreat`, `getApiStatus`, types |
| `src/api/ariaApi.ts` | ARIA chat client |
| `src/api/ubaApi.ts` | UBA tracking + dashboard |

### Custom hooks

| File | Purpose |
|---|---|
| `src/hooks/useThreatPredict.ts` | Wraps prediction call with loading/error state |
| `src/hooks/useAudioAlert.ts` | Plays alert sound on threat level change |

---

## Run & maintain

### Force a model retrain
```bash
RETRAIN_MODELS=1 python backend_final.py
```

### Reset everything
```bash
del models_cache.pkl threat_model.pkl scaler.pkl label_encoder.pkl
python train_model.py
python backend_final.py
```

### Re-enable verbose logs
```bash
LOG_LEVEL=DEBUG python backend_final.py
```

### Switch UBA to PostgreSQL
```bash
DATABASE_URL=postgresql://user:pass@host/db python backend_final.py
```

### Production deployment hint
The `app.run()` Flask dev server is for development only. For prod, run with a real WSGI server:
```bash
pip install waitress
waitress-serve --port=5000 backend.app:create_app
```

---

## Dataset & models

| File | Source | Size | Purpose |
|---|---|---|---|
| `KDDTrain+.txt` | NSL-KDD via `download_dataset.py` | 19 MB | Training data, 125,973 rows × 42 cols |
| `threat_model.pkl` | `train_model.py` | ~5 MB | 3-class threat-level RF |
| `scaler.pkl` | `train_model.py` | <1 KB | StandardScaler for the threat model |
| `label_encoder.pkl` | `train_model.py` | <1 KB | LabelEncoder for `LOW/MEDIUM/HIGH` |
| `models_cache.pkl` | `backend.models.cache.save()` | ~30 MB | All other models + heatmap + samples |
| `uba_logs.db` | `backend.uba` (auto) | grows | SQLite UBA database |

---

## Acceptance criteria (verified)

- [x] `python backend_final.py` boots in ~1 s on cache hit
- [x] All 13 endpoints respond with HTTP 200 and identical JSON to original
- [x] `/health` returns deep subsystem status, 503 when degraded
- [x] No Gemini deprecation warnings on boot
- [x] CPU stays usable during retraining (bounded n_jobs)
- [x] Frontend `pnpm dev` works against new backend without code changes
- [x] Existing start scripts (`start_backend.bat`, etc.) work unchanged
- [x] `.env` properly gitignored
