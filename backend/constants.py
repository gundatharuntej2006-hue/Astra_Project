"""Static lookup tables and feature definitions.

Pure data — no I/O, no state. Safe to import anywhere.
"""

FEATURES = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes", "land",
    "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in", "num_compromised",
    "root_shell", "su_attempted", "num_root", "num_file_creations", "num_shells",
    "num_access_files", "num_outbound_cmds", "is_host_login", "is_guest_login",
    "count", "srv_count", "serror_rate", "srv_serror_rate", "rerror_rate", "srv_rerror_rate",
    "same_srv_rate", "diff_srv_rate", "srv_diff_host_rate", "dst_host_count",
    "dst_host_srv_count", "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate", "dst_host_serror_rate",
    "dst_host_srv_serror_rate", "dst_host_rerror_rate", "dst_host_srv_rerror_rate",
]

DATASET_COLUMNS = FEATURES + ["label", "difficulty"]

# Mock IP ranges keyed by attack type — used for demo geolocation.
REGION_IPS = {
    "DoS":    ["103.24.76.0", "185.156.172.0"],
    "Probe":  ["91.240.118.0", "193.163.125.0"],
    "R2L":    ["218.92.0.0"],
    "U2R":    ["45.143.203.0"],
    "Normal": ["12.0.0.0"],
}

DOS_ATTACKS = {
    "neptune", "smurf", "pod", "teardrop", "land", "back",
    "apache2", "udpstorm", "processtable", "mailbomb",
    "snmpgetattack", "snmpguess", "worm", "crashiis",
}
PROBE_ATTACKS = {"portsweep", "satan", "nmap", "ipsweep", "mscan", "saint"}
R2L_ATTACKS = {
    "warezclient", "guess_passwd", "warezmaster", "imap", "ftp_write",
    "multihop", "phf", "spy", "named",
    "xlock", "xsnoop", "sendmail", "httptunnel",
}
U2R_ATTACKS = {"buffer_overflow", "rootkit", "loadmodule", "perl", "sqlattack", "xterm", "ps"}

HIGH_THREAT_LABELS = {
    "neptune", "smurf", "pod", "teardrop", "land", "back",
    "apache2", "udpstorm", "processtable", "mailbomb",
}


def map_attack_category(label):
    """Map an NSL-KDD raw label to one of: Normal, DoS, Probe, R2L, U2R."""
    label = label.strip().lower()
    if label == "normal":
        return "Normal"
    if label in DOS_ATTACKS:
        return "DoS"
    if label in PROBE_ATTACKS:
        return "Probe"
    if label in R2L_ATTACKS:
        return "R2L"
    if label in U2R_ATTACKS:
        return "U2R"
    return "DoS"  # legacy fallback — preserved for behavior parity


def map_threat(label):
    """Map an NSL-KDD raw label to a threat level: LOW, MEDIUM, HIGH."""
    if label == "normal":
        return "LOW"
    if label in HIGH_THREAT_LABELS:
        return "HIGH"
    return "MEDIUM"
