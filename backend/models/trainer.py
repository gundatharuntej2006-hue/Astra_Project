"""Train all ML models from the NSL-KDD dataset and write them into `state`.

This is invoked on first boot (or when the cache is stale). On subsequent boots
the cache module restores the same state from disk.
"""
import logging

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


def train_all_models(file_path):
    """Train every model the dashboard needs and write them into `backend.state`."""
    logger.info("Loading dataset from: %s", file_path)
    df = pd.read_csv(file_path, header=None, names=DATASET_COLUMNS)
    df.drop("difficulty", axis=1, inplace=True)
    logger.info("Dataset loaded: %s", df.shape)

    raw_labels = df["label"].copy()

    # ─── Part A: Threat-level metrics (RF vs LR comparison) ─────────────
    df_threat = df.copy()
    df_threat["threat_level"] = df_threat["label"].apply(map_threat)
    df_threat.drop("label", axis=1, inplace=True)

    le = LabelEncoder()
    for col_name in ["protocol_type", "service", "flag"]:
        df_threat[col_name] = le.fit_transform(df_threat[col_name])

    le2 = LabelEncoder()
    df_threat["threat_level"] = le2.fit_transform(df_threat["threat_level"])
    classes = le2.classes_.tolist()

    X = df_threat.drop("threat_level", axis=1)
    y = df_threat["threat_level"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    sc = StandardScaler()
    X_train_s = sc.fit_transform(X_train)
    X_test_s = sc.transform(X_test)

    logger.info("Training Random Forest (threat level)...")
    rf = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=2)
    rf.fit(X_train_s, y_train)
    rf_pred = rf.predict(X_test_s)
    rf_acc = round(accuracy_score(y_test, rf_pred) * 100, 2)
    rf_cm = confusion_matrix(y_test, rf_pred).tolist()

    logger.info("Training Logistic Regression (threat level)...")
    lr = LogisticRegression(max_iter=500, random_state=42)
    lr.fit(X_train_s, y_train)
    lr_pred = lr.predict(X_test_s)
    lr_acc = round(accuracy_score(y_test, lr_pred) * 100, 2)
    lr_cm = confusion_matrix(y_test, lr_pred).tolist()

    state.METRICS = {
        "classes":             classes,
        "random_forest":       {"accuracy": rf_acc, "confusion_matrix": rf_cm},
        "logistic_regression": {"accuracy": lr_acc, "confusion_matrix": lr_cm},
    }

    # ─── Part B: 5-class attack category classifier ─────────────────────
    logger.info("Training 5-class attack category classifier...")
    df_attack = df.copy()
    df_attack["attack_category"] = df_attack["label"].apply(map_attack_category)
    df_attack.drop("label", axis=1, inplace=True)

    le3 = LabelEncoder()
    for col_name in ["protocol_type", "service", "flag"]:
        df_attack[col_name] = le3.fit_transform(df_attack[col_name])

    attack_le = LabelEncoder()
    df_attack["attack_category"] = attack_le.fit_transform(df_attack["attack_category"])

    X_atk = df_attack.drop("attack_category", axis=1)
    y_atk = df_attack["attack_category"]
    X_atk_train, X_atk_test, y_atk_train, y_atk_test = train_test_split(
        X_atk, y_atk, test_size=0.2, random_state=42
    )

    attack_sc = StandardScaler()
    X_atk_train_s = attack_sc.fit_transform(X_atk_train)
    X_atk_test_s = attack_sc.transform(X_atk_test)

    # Bounded thread count keeps the box responsive during training.
    attack_rf = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=2)
    attack_rf.fit(X_atk_train_s, y_atk_train)
    atk_pred = attack_rf.predict(X_atk_test_s)
    atk_acc = round(accuracy_score(y_atk_test, atk_pred) * 100, 2)
    atk_cm = confusion_matrix(y_atk_test, atk_pred).tolist()

    state.ATTACK_MODEL = attack_rf
    state.ATTACK_SCALER = attack_sc
    state.ATTACK_LE = attack_le

    state.METRICS["attack_classifier"] = {
        "accuracy": atk_acc,
        "confusion_matrix": atk_cm,
        "classes": attack_le.classes_.tolist(),
    }

    # ─── Part C: Isolation Forest (anomaly detection) ───────────────────
    logger.info("Training Isolation Forest (anomaly detection)...")
    iso_sc = StandardScaler()
    X_iso = iso_sc.fit_transform(X_atk)
    iso_model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42, n_jobs=2)
    iso_model.fit(X_iso)
    state.ISOLATION_MODEL = iso_model
    state.ISOLATION_SCALER = iso_sc
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

    reset_shap_cache()  # The model just changed — old per-input cache entries are stale.

    # ─── Part E: Heatmap data ───────────────────────────────────────────
    logger.info("Computing heatmap data...")
    try:
        df_hm = df.copy()
        df_hm["attack_category"] = df_hm["label"].apply(map_attack_category)
        proto_map_rev = {"tcp": "TCP", "udp": "UDP", "icmp": "ICMP"}
        svc_set = {"http", "ftp", "ftp_data", "smtp", "ssh", "domain_u"}
        heatmap = {}
        for _, row in df_hm.iterrows():
            proto = proto_map_rev.get(str(row["protocol_type"]).lower(), "OTHER")
            svc_raw = str(row["service"]).lower()
            if svc_raw in svc_set:
                svc = svc_raw.upper().replace("FTP_DATA", "FTP").replace("DOMAIN_U", "DNS")
            else:
                svc = "Other"
            key = f"{proto}_{svc}"
            if key not in heatmap:
                heatmap[key] = {}
            cat = row["attack_category"]
            heatmap[key][cat] = heatmap[key].get(cat, 0) + 1
        state.HEATMAP_DATA = heatmap
        logger.info("Heatmap data ready.")
    except Exception as e:
        logger.error("Heatmap error: %s", e)
        state.HEATMAP_DATA = {}

    # ─── Part F: Sample connections for simulation ──────────────────────
    logger.info("Selecting sample connections...")
    try:
        df_sim = df.copy()
        df_sim["attack_category"] = raw_labels.apply(map_attack_category)
        samples = []
        for cat in ["Normal", "DoS", "Probe", "R2L", "U2R"]:
            cat_df = df_sim[df_sim["attack_category"] == cat]
            picked = cat_df.sample(n=4, random_state=42) if len(cat_df) >= 4 else cat_df
            for _, row in picked.iterrows():
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
        logger.info("Sample connections: %d", len(samples))
    except Exception as e:
        logger.error("Sample connections error: %s", e)
        state.SAMPLE_CONNECTIONS = []

    logger.info("All models ready!")
