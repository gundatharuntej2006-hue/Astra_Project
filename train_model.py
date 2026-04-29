import joblib
import pandas as pd
import numpy as np
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler

FEATURES = [
    "duration","protocol_type","service","flag","src_bytes","dst_bytes","land",
    "wrong_fragment","urgent","hot","num_failed_logins","logged_in","num_compromised",
    "root_shell","su_attempted","num_root","num_file_creations","num_shells",
    "num_access_files","num_outbound_cmds","is_host_login","is_guest_login",
    "count","srv_count","serror_rate","srv_serror_rate","rerror_rate","srv_rerror_rate",
    "same_srv_rate","diff_srv_rate","srv_diff_host_rate","dst_host_count",
    "dst_host_srv_count","dst_host_same_srv_rate","dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate","dst_host_srv_diff_host_rate","dst_host_serror_rate",
    "dst_host_srv_serror_rate","dst_host_rerror_rate","dst_host_srv_rerror_rate"
]

cols = FEATURES + ["label", "difficulty"]

print("Loading dataset...")
df = pd.read_csv("KDDTrain+.txt", header=None, names=cols)
df.drop("difficulty", axis=1, inplace=True)

def map_threat(label):
    if label == "normal": return "LOW"
    elif label in ["neptune","smurf","pod","teardrop","land","back",
                   "apache2","udpstorm","processtable","mailbomb"]: return "HIGH"
    else: return "MEDIUM"

print("Preprocessing...")
df["threat_level"] = df["label"].apply(map_threat)
df.drop("label", axis=1, inplace=True)

# Mappings from app_fixed.py
proto_map = {"tcp": 2, "udp": 1, "icmp": 0}
service_map = {"http": 10, "ftp_data": 4, "ftp": 4, "smtp": 18, "ssh": 20, "domain_u": 3, "dns": 3}
# Map others to 0
flag_map = {"SF": 5, "S0": 4, "REJ": 3, "RSTO": 2, "SH": 1}

df["protocol_type"] = df["protocol_type"].map(proto_map).fillna(0).astype(int)
df["service"] = df["service"].map(service_map).fillna(0).astype(int)
df["flag"] = df["flag"].map(flag_map).fillna(0).astype(int)

le_target = LabelEncoder()
df["threat_level"] = le_target.fit_transform(df["threat_level"])

X = df.drop("threat_level", axis=1)
y = df["threat_level"]

print("Scaling...")
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

print("Training Random Forest...")
# Memory-tuned for Render's 512MB free tier. Override locally with RF_ESTIMATORS env var.
n_est = int(os.environ.get("RF_ESTIMATORS", "20"))
model = RandomForestClassifier(n_estimators=n_est, random_state=42, n_jobs=1)
X_scaled = X_scaled.astype(np.float32)
model.fit(X_scaled, y)

print("Saving models...")
joblib.dump(model, "threat_model.pkl")
joblib.dump(scaler, "scaler.pkl")
joblib.dump(le_target, "label_encoder.pkl")

print("Done!")
print(f"Classes saved: {le_target.classes_}")
