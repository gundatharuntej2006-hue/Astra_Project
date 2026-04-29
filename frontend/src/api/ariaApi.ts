const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

export interface AriaMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface DashboardContext {
  lastThreat?: string;
  lastAttackType?: string;
  lastConfidence?: number;
  isAnomalous?: boolean;
  shapValues?: { feature: string; value: number }[];
}

export interface AriaChatResponse {
  success: boolean;
  data: { reply: string; session_id: string } | null;
  error: string | null;
}

export async function sendAriaMessage(
  message: string,
  sessionId: string,
  dashboardContext?: DashboardContext
): Promise<AriaChatResponse> {
  const res = await fetch(`${BASE_URL}/aria-chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      dashboard_context: dashboardContext || null,
    }),
  });
  if (!res.ok) throw new Error(`ARIA API error: ${res.status}`);
  return res.json();
}

export async function clearAriaSession(sessionId: string): Promise<void> {
  await fetch(`${BASE_URL}/aria-clear`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
}
