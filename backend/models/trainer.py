"""Train all ML models from the NSL-KDD dataset and write them into `state`.

This is invoked on first boot (or when the cache is stale). On subsequent boots
the cache module restores the same state from disk.

Memory-tuned for Render's 512 MB free tier:
  - Heatmap + sample-connections built FIRST, before the heavy training,
    so we can drop the full dataframe before RF.fit() starts.
  - Smaller forests (n_estimators=15 default).
  - float32 scaled matrices instead of float64.
  - Aggressive `del` between stages (must be in-scope, not via helper).
"""
import gc
import logging
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from backend import state
from backend.constants import (
    DATASET_COLUMNS,
    FEATURES,
    map_attack_category,
    map_threat,
)
from backend.models.inference import reset_shap_cache

logger = logging.getLogger("soc.trainer")

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("shap not installed. SHAP values will not be available.")


# Forest sizes tuned for 512 MB free tier. Override via env vars on bigger hosts.
RF_ESTIMATORS = int(os.getenv("RF_ESTIMATORS", "15"))
ISO_ESTIMATORS = int(os.getenv("ISO_ESTIMATORS", "30"))


def train_all_models(file_path):
    """Train every model the dashboard needs and write them into `backend.state`."""
    logger.info("Loading dataset from: %s", file_path)
    df = pd.read_csv(file_path, header=None, names=DATASET_COLUMNS)
    df.drop("difficulty", axis=1, inplace=True)
    logger.info("Dataset loaded: %s", df.shape)

    # ─── Part E (moved up): Heatmap data — needs raw `df` ────────────────
    logger.info("Computing heatmap data...")
    proto_map_rev = {"tcp": "TCP", "udp": "UDP", "icmp": "ICMP"}
    svc_set = {"http", "ftp", "ftp_data", "smtp", "ssh", "domain_u"}
    heatmap = {}
    try:
        protos = df["protocol_type"].astype(str).str.lower().to_numpy()
        services = df["service"].astype(str).str.lower().to_numpy()
        cats_full = df["label"].apply(map_attack_category).to_numpy()
        for proto_raw, svc_raw, cat in zip(protos, services, cats_full):
            proto = proto_map_rev.get(proto_raw, "OTHER")
            if svc_raw in svc_set:
                svc = svc_raw.upper().replace("FTP_DATA", "FTP").replace("DOMAIN_U", "DNS")
            else:
                svc = "Other"
            key = f"{proto}_{svc}"
            slot = heatmap.setdefault(key, {})
            slot[cat] = slot.get(cat, 0) + 1
        del protos, services
        state.HEATMAP_DATA = heatmap
        logger.info("Heatmap data ready.")
    except Exception as e:
        logger.error("Heatmap error: %s", e)
        state.HEATMAP_DATA = {}

    # ─── Part F (moved up): Sample connections — needs raw `df` ──────────
    logger.info("Selecting sample connections...")
    samples = []
    try:
        # Build a small index → category map without copying the full df.
        cat_series = pd.Series(cats_full, index=df.index)
        for cat in ["Normal", "DoS", "Probe", "R2L", "U2R"]:
            cat_idx = cat_series.index[cat_series == cat]
            if len(cat_idx) >= 4:
                cat_idx = cat_idx[:4]
            for i in cat_idx:
                row = df.iloc[i]
                sample = {f: 0 for f in FEATURES}
                for f in FEATURES:
                    val = row.get(f, 0)
                    try:
                        sample[f] = float(val) if not isinstance(val, str) else 0
                    except (ValueError, TypeError):
                        sample[f] = 0
                sample["_attack_category"] = cat
                samples.append(sample)
        state.SAMPLE_CONNECTIONS = samples
        del cat_series, cats_full
        logger.info("Sample connections: %d", len(samples))
    except Exception as e:
        logger.error("Sample connections error: %s", e)
        state.SAMPLE_CONNECTIONS = []

    # ─── Part A: Threat-level metrics (RF vs LR comparison) ─────────────
    df_threat = df  # reuse — we'll mutate in place
    df_threat["threat_level"] = df_threat["label"].apply(map_threat)
    df_threat.drop("label", axis=1, inplace=True)

    le = LabelEncoder()
    for col_name in ["protocol_type", "service", "flag"]:
        df_threat[col_name] = le.fit_transform(df_threat[col_name])

    le2 = LabelEncoder()
    df_threat["threat_level"] = le2.fit_transform(df_threat["threat_level"])
    classes = le2.classes_.tolist()

    X = df_threat.drop("threat_level", axis=1).to_numpy(dtype=np.float32)
    y = df_threat["threat_level"].to_numpy()
    del df_threat, df  # full dataframe is no longer needed
    gc.collect()

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    del X, y
    gc.collect()

    sc = StandardScaler()
    X_train_s = sc.fit_transform(X_train).astype(np.float32)
    X_test_s = sc.transform(X_test).astype(np.float32)
    del X_train, X_test
    gc.collect()

    logger.info("Training Random Forest (threat level, n_estimators=%d)...", RF_ESTIMATORS)
    rf = RandomForestClassifier(n_estimators=RF_ESTIMATORS, random_state=42, n_jobs=1)
    rf.fit(X_train_s, y_train)
    rf_pred = rf.predict(X_test_s)
    rf_acc = round(accuracy_score(y_test, rf_pred) * 100, 2)
    rf_cm = confusion_matrix(y_test, rf_pred).tolist()
    del rf, rf_pred
    gc.collect()

    logger.info("Training Logistic Regression (threat level)...")
    lr = LogisticRegression(max_iter=500, random_state=42)
    lr.fit(X_train_s, y_train)
    lr_pred = lr.predict(X_test_s)
    lr_acc = round(accuracy_score(y_test, lr_pred) * 100, 2)
    lr_cm = confusion_matrix(y_test, lr_pred).tolist()
    del lr, lr_pred, X_train_s, X_test_s, y_train, y_test, sc
    gc.collect()

    state.METRICS = {
        "classes":             classes,
        "random_forest":       {"accuracy": rf_acc, "confusion_matrix": rf_cm},
        "logistic_regression": {"accuracy": lr_acc, "confusion_matrix": lr_cm},
    }

    # ─── Part B: 5-class attack category classifier ─────────────────────
    # Load only the feature columns + label fresh, since `df` was already freed.
    logger.info("Re-loading dataset for 5-class classifier...")
    df_attack = pd.read_csv(file_path, header=None, names=DATASET_COLUMNS)
    df_attack.drop("difficulty", axis=1, inplace=True)
    df_attack["attack_category"] = df_attack["label"].apply(map_attack_category)
    df_attack.drop("label", axis=1, inplace=True)

    le3 = LabelEncoder()
    for col_name in ["protocol_type", "service", "flag"]:
        df_attack[col_name] = le3.fit_transform(df_attack[col_name])

    attack_le = LabelEncoder()
    df_attack["attack_category"] = attack_le.fit_transform(df_attack["attack_category"])

    X_atk = df_attack.drop("attack_category", axis=1).to_numpy(dtype=np.float32)
    y_atk = df_attack["attack_category"].to_numpy()
    del df_attack
    gc.collect()

    X_atk_train, X_atk_test, y_atk_train, y_atk_test = train_test_split(
        X_atk, y_atk, test_size=0.2, random_state=42
    )

    attack_sc = StandardScaler()
    X_atk_train_s = attack_sc.fit_transform(X_atk_train).astype(np.float32)
    X_atk_test_s = attack_sc.transform(X_atk_test).astype(np.float32)
    del X_atk_train, X_atk_test
    gc.collect()

    logger.info("Training 5-class attack category classifier (n_estimators=%d)...", RF_ESTIMATORS)
    attack_rf = RandomForestClassifier(n_estimators=RF_ESTIMATORS, random_state=42, n_jobs=1)
    attack_rf.fit(X_atk_train_s, y_atk_train)
    atk_pred = attack_rf.predict(X_atk_test_s)
    atk_acc = round(accuracy_score(y_atk_test, atk_pred) * 100, 2)
    atk_cm = confusion_matrix(y_atk_test, atk_pred).tolist()
    del X_atk_train_s, X_atk_test_s, y_atk_train, y_atk_test, atk_pred
    gc.collect()

    state.ATTACK_MODEL = attack_rf
    state.ATTACK_SCALER = attack_sc
    state.ATTACK_LE = attack_le

    state.METRICS["attack_classifier"] = {
        "accuracy": atk_acc,
        "confusion_matrix": atk_cm,
        "classes": attack_le.classes_.tolist(),
    }

    # ─── Part C: Isolation Forest (anomaly detection) ───────────────────
    logger.info("Training Isolation Forest (n_estimators=%d)...", ISO_ESTIMATORS)
    iso_sc = StandardScaler()
    X_iso = iso_sc.fit_transform(X_atk).astype(np.float32)
    del X_atk, y_atk
    gc.collect()

    iso_model = IsolationForest(
        n_estimators=ISO_ESTIMATORS, contamination=0.1, random_state=42, n_jobs=1
    )
    iso_model.fit(X_iso)
    state.ISOLATION_MODEL = iso_model
    state.ISOLATION_SCALER = iso_sc
    del X_iso
    gc.collect()
    logger.info("Isolation Forest ready.")

    # ─── Part D: SHAP Explainer ─────────────────────────────────────────
    if SHAP_AVAILABLE:
        logger.info("Creating SHAP TreeExplainer...")
        try:
            state.SHAP_EXPLAINER = shap.TreeExplainer(attack_rf)
            logger.info("SHAP explainer ready.")
        except Exception as e:
            logger.error("SHAP explainer creation failed: %s", e)
            state.SHAP_EXPLAINER = None
    else:
        state.SHAP_EXPLAINER = None

    reset_shap_cache()
    logger.info("All models ready!")
