const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

export interface ThreatInput {
  duration: number;
  protocol_type: number;
  service: number;
  flag: number;
  src_bytes: number;
  dst_bytes: number;
  land: number;
  wrong_fragment: number;
  urgent: number;
  hot: number;
  num_failed_logins: number;
  logged_in: number;
  num_compromised: number;
  root_shell: number;
  su_attempted: number;
  num_root: number;
  num_file_creations: number;
  num_shells: number;
  num_access_files: number;
  num_outbound_cmds: number;
  is_host_login: number;
  is_guest_login: number;
  count: number;
  srv_count: number;
  serror_rate: number;
  srv_serror_rate: number;
  rerror_rate: number;
  srv_rerror_rate: number;
  same_srv_rate: number;
  diff_srv_rate: number;
  srv_diff_host_rate: number;
  dst_host_count: number;
  dst_host_srv_count: number;
  dst_host_same_srv_rate: number;
  dst_host_diff_srv_rate: number;
  dst_host_same_src_port_rate: number;
  dst_host_srv_diff_host_rate: number;
  dst_host_serror_rate: number;
  dst_host_srv_serror_rate: number;
  dst_host_rerror_rate: number;
  dst_host_srv_rerror_rate: number;
}

export type AttackType = "Normal" | "DoS" | "Probe" | "R2L" | "U2R";

export interface ShapValue {
  feature: string;
  value: number;
}

export interface XAIContribution {
  feature: string;
  value: number;
  raw_value: number;
  shap_value: number;
  abs_shap: number;
  direction: "increases_risk" | "decreases_risk";
  pct: number;
}

export interface XAIPayload {
  top3_reasons: string[];
  top_contributions: XAIContribution[];
  predicted_class: string;
  class_labels: string[];
}

export interface ThreatResponse {
  threat: "LOW" | "MEDIUM" | "HIGH";
  confidence: number;
  probabilities: { LOW: number; MEDIUM: number; HIGH: number };
  attack_type?: AttackType;
  attack_probabilities?: Record<AttackType, number>;
  shap_values?: ShapValue[];
  xai?: XAIPayload | null;
  is_anomalous?: boolean;
  anomaly_score?: number;
  location?: { lat: number; lng: number; city: string; country: string; ip: string };
}

export interface BatchResult {
  index: number;
  threat: string;
  confidence: number;
  attack_type: string;
  is_anomalous?: boolean;
  anomaly_score?: number;
  probability?: number;
  error?: string;
}

export interface BatchResponse {
  success: boolean;
  data: {
    total: number;
    results: BatchResult[];
    attack_breakdown: Record<string, number>;
    threat_breakdown: Record<string, number>;
  } | null;
  error: string | null;
}

export interface PredictionHistoryEntry {
  id: string;
  timestamp: string;
  protocol: string;
  service: string;
  flag: string;
  threatLevel: "LOW" | "MEDIUM" | "HIGH";
  attackType: string;
  confidence: number;
  isAnomalous: boolean;
  shapValues?: ShapValue[];
  input: ThreatInput;
}

export async function predictThreat(input: ThreatInput): Promise<ThreatResponse> {
  const res = await fetch(`${BASE_URL}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function batchPredict(file: File): Promise<BatchResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BASE_URL}/predict-batch`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`Batch API error: ${res.status}`);
  return res.json();
}

export async function getHeatmapData(): Promise<{ success: boolean; data: Record<string, Record<string, number>>; error: string | null }> {
  const res = await fetch(`${BASE_URL}/heatmap-data`);
  if (!res.ok) throw new Error(`Heatmap API error: ${res.status}`);
  return res.json();
}

export async function getSampleConnections(): Promise<{ success: boolean; data: ThreatInput[]; error: string | null }> {
  const res = await fetch(`${BASE_URL}/sample-connections`);
  if (!res.ok) throw new Error(`Sample API error: ${res.status}`);
  return res.json();
}

export async function generateReport(predData: Record<string, unknown>): Promise<{ success: boolean; data: { report: string }; error: string | null }> {
  const res = await fetch(`${BASE_URL}/generate-report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(predData),
  });
  if (!res.ok) throw new Error(`Report API error: ${res.status}`);
  return res.json();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

export async function uploadDataset(file: File): Promise<{ status: string; message: string }> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BASE_URL}/upload-dataset`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || `Upload failed: ${res.status}`);
  }
  return res.json();
}

export interface ApiStatus {
  gemini: boolean;
  ipstack: boolean;
  shap: boolean;
  aria: boolean;
  attack_classifier: boolean;
  isolation_forest: boolean;
}

export async function getApiStatus(): Promise<ApiStatus> {
  try {
    const res = await fetch(`${BASE_URL}/api-status`);
    if (!res.ok) throw new Error('API status check failed');
    const json = await res.json();
    return json.data;
  } catch {
    return {
      gemini: false,
      ipstack: false,
      shap: false,
      aria: false,
      attack_classifier: false,
      isolation_forest: false,
    };
  }
}
