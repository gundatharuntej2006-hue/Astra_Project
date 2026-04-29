"""User Behavior Analytics — per-user Isolation Forest + risk scoring.

SQLAlchemy-backed (SQLite by default, swap via DATABASE_URL env var).
Registered as a Flask blueprint at /api/uba/*.
"""
import logging
import os
import random
from datetime import datetime, timedelta

import numpy as np
from flask import Blueprint, jsonify, request
from sklearn.ensemble import IsolationForest
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import BASE_DIR

logger = logging.getLogger("soc.uba")

uba_bp = Blueprint("uba", __name__, url_prefix="/api/uba")

DB_PATH = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'uba_logs.db')}")
engine = create_engine(
    DB_PATH,
    connect_args={"check_same_thread": False} if DB_PATH.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserActivity(Base):
    __tablename__ = "user_activities"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String)  # login, download, upload, file_access, failed_login
    ip_address = Column(String)
    device_type = Column(String)
    location = Column(String)
    data_transferred_mb = Column(Float, default=0.0)
    session_duration_min = Column(Float, default=0.0)
    is_anomalous = Column(Boolean, default=False)
    anomaly_score = Column(Float, default=0.0)
    risk_level = Column(String, default="Low")


class UserRisk(Base):
    __tablename__ = "user_risks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    current_risk_score = Column(Float, default=0.0)
    risk_level = Column(String, default="Low")
    last_updated = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

# In-memory per-user model cache. Repopulates from DB on first detection.
uba_models = {}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def extract_features(activity):
    """Numerical features for the Isolation Forest."""
    hour = activity.timestamp.hour
    data_mb = activity.data_transferred_mb
    duration = activity.session_duration_min
    failed_login = 1 if activity.action == "failed_login" else 0
    return [hour, data_mb, duration, failed_login]


def train_user_baseline(db, user_id):
    """Train per-user Isolation Forest from historical activities."""
    activities = db.query(UserActivity).filter(UserActivity.user_id == user_id).all()
    if len(activities) < 10:
        return  # Not enough data for a reliable baseline
    features = [extract_features(a) for a in activities]
    model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
    model.fit(features)
    uba_models[user_id] = model


def detect_anomaly(db, user_id, activity):
    """Detect if an activity is anomalous. Returns (is_anomaly, score)."""
    if user_id not in uba_models:
        train_user_baseline(db, user_id)

    model = uba_models.get(user_id)
    features = extract_features(activity)

    if model is None:
        # Rule-based fallback when there's no model yet.
        score = 0.0
        if activity.action == "failed_login":
            score += 30
        if activity.data_transferred_mb > 1000:
            score += 50
        if activity.timestamp.hour < 5 or activity.timestamp.hour > 23:
            score += 20
        return score >= 50, score

    pred = model.predict([features])[0]
    raw_score = model.decision_function([features])[0]
    normalized_score = max(0, min(100, (-raw_score + 0.5) * 100))

    if activity.action == "failed_login":
        normalized_score = min(100, normalized_score + 40)
    if activity.data_transferred_mb > 5000:
        normalized_score = min(100, normalized_score + 50)

    is_anom = bool(pred == -1 or normalized_score > 60)
    return is_anom, normalized_score


def update_user_risk(db, user_id, anomaly_score):
    """Smoothly update the aggregate risk score for a user."""
    risk = db.query(UserRisk).filter(UserRisk.user_id == user_id).first()
    if not risk:
        risk = UserRisk(user_id=user_id, current_risk_score=0.0)
        db.add(risk)

    risk.current_risk_score = (risk.current_risk_score * 0.7) + (anomaly_score * 0.3)

    if risk.current_risk_score > 70:
        risk.risk_level = "High"
    elif risk.current_risk_score > 40:
        risk.risk_level = "Medium"
    else:
        risk.risk_level = "Low"

    risk.last_updated = datetime.utcnow()
    db.commit()
    return risk


@uba_bp.route("/track", methods=["POST"])
def track_activity():
    data = request.json
    db = next(get_db())

    try:
        user_id = data.get("user_id", "unknown")
        activity = UserActivity(
            user_id=user_id,
            action=data.get("action", "unknown"),
            ip_address=data.get("ip_address", "0.0.0.0"),
            device_type=data.get("device_type", "unknown"),
            location=data.get("location", "Unknown"),
            data_transferred_mb=float(data.get("data_transferred_mb", 0)),
            session_duration_min=float(data.get("session_duration_min", 0)),
        )

        is_anom, score = detect_anomaly(db, user_id, activity)
        activity.is_anomalous = is_anom
        activity.anomaly_score = score

        if score > 70:
            activity.risk_level = "High"
        elif score > 40:
            activity.risk_level = "Medium"
        else:
            activity.risk_level = "Low"

        db.add(activity)
        db.commit()
        db.refresh(activity)

        risk = update_user_risk(db, user_id, score)

        return jsonify({
            "success":         True,
            "activity_id":     activity.id,
            "is_anomalous":    is_anom,
            "anomaly_score":   round(score, 2),
            "user_risk_level": risk.risk_level,
            "user_risk_score": round(risk.current_risk_score, 2),
        })
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@uba_bp.route("/dashboard", methods=["GET"])
def get_dashboard_data():
    db = next(get_db())
    try:
        recent = db.query(UserActivity).order_by(UserActivity.timestamp.desc()).limit(50).all()
        high_risk = (
            db.query(UserRisk)
            .filter(UserRisk.risk_level.in_(["High", "Medium"]))
            .order_by(UserRisk.current_risk_score.desc())
            .all()
        )
        anomalies = (
            db.query(UserActivity)
            .filter(UserActivity.is_anomalous == True)  # noqa: E712
            .order_by(UserActivity.timestamp.desc())
            .limit(10)
            .all()
        )

        return jsonify({
            "success": True,
            "recent_activities": [
                {
                    "id":           a.id,
                    "user_id":      a.user_id,
                    "action":       a.action,
                    "time":         a.timestamp.isoformat(),
                    "is_anomalous": a.is_anomalous,
                    "score":        a.anomaly_score,
                    "risk_level":   a.risk_level,
                }
                for a in recent
            ],
            "risk_scores": [
                {"user_id": r.user_id, "score": round(r.current_risk_score, 2), "level": r.risk_level}
                for r in high_risk
            ],
            "alerts": [
                {
                    "user_id": a.user_id,
                    "action":  a.action,
                    "time":    a.timestamp.isoformat(),
                    "details": f"Score: {round(a.anomaly_score, 2)} - Data: {a.data_transferred_mb}MB",
                }
                for a in anomalies
            ],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@uba_bp.route("/simulate", methods=["POST"])
def simulate_data():
    """Inject sample scenarios for the demo."""
    db = next(get_db())
    data = request.json
    scenario = data.get("scenario", "normal")
    user_id = data.get("user_id", "jdoe")

    # Seed baseline history if missing.
    history = db.query(UserActivity).filter(UserActivity.user_id == user_id).count()
    if history < 15:
        base_time = datetime.utcnow() - timedelta(days=5)
        for i in range(15):
            db.add(UserActivity(
                user_id=user_id,
                action="login",
                timestamp=base_time + timedelta(days=i * 0.3, hours=random.randint(9, 17)),
                data_transferred_mb=random.uniform(5, 50),
                session_duration_min=random.uniform(10, 120),
                is_anomalous=False,
                anomaly_score=random.uniform(0, 10),
                risk_level="Low",
            ))
        db.commit()
        train_user_baseline(db, user_id)

    now = datetime.utcnow()
    activities_to_add = []

    if scenario == "3am_login":
        activities_to_add.append(UserActivity(
            user_id=user_id, action="login", timestamp=now.replace(hour=3),
            data_transferred_mb=5.0, location="Unknown",
        ))
    elif scenario == "large_download":
        activities_to_add.append(UserActivity(
            user_id=user_id, action="download", timestamp=now,
            data_transferred_mb=8500.0, location="Local",
        ))
    elif scenario == "new_country":
        activities_to_add.append(UserActivity(
            user_id=user_id, action="login", timestamp=now,
            data_transferred_mb=2.0, location="Russia",
        ))
    elif scenario == "brute_force":
        for i in range(5):
            activities_to_add.append(UserActivity(
                user_id=user_id, action="failed_login",
                timestamp=now - timedelta(minutes=5 - i),
                data_transferred_mb=0.1,
            ))
        activities_to_add.append(UserActivity(
            user_id=user_id, action="login", timestamp=now, data_transferred_mb=1.0,
        ))
    else:  # normal
        activities_to_add.append(UserActivity(
            user_id=user_id, action="file_access", timestamp=now,
            data_transferred_mb=12.0, location="Local",
        ))

    results = []
    for act in activities_to_add:
        is_anom, score = detect_anomaly(db, user_id, act)
        act.is_anomalous = is_anom
        act.anomaly_score = score

        if score > 70:
            act.risk_level = "High"
        elif score > 40:
            act.risk_level = "Medium"
        else:
            act.risk_level = "Low"

        db.add(act)
        db.commit()
        db.refresh(act)
        update_user_risk(db, user_id, score)

        results.append({
            "action":        act.action,
            "is_anomalous":  is_anom,
            "anomaly_score": round(score, 2),
            "risk_level":    act.risk_level,
        })

    return jsonify({"success": True, "results": results})


def setup_uba(app):
    app.register_blueprint(uba_bp)
    logger.info("UBA Module Initialized and Registered.")
