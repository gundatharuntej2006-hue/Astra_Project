const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000') + '/api/uba';

export interface UbaActivity {
  id: number;
  user_id: string;
  action: string;
  time: string;
  is_anomalous: boolean;
  score: number;
  risk_level: string;
}

export interface UbaRisk {
  user_id: string;
  score: number;
  level: string;
}

export interface UbaAlert {
  user_id: string;
  action: string;
  time: string;
  details: string;
}

export interface UbaDashboardData {
  recent_activities: UbaActivity[];
  risk_scores: UbaRisk[];
  alerts: UbaAlert[];
}

export const fetchUbaDashboard = async (): Promise<UbaDashboardData> => {
  const response = await fetch(`${API_BASE_URL}/dashboard`);
  if (!response.ok) {
    throw new Error('Failed to fetch UBA dashboard data');
  }
  const data = await response.json();
  if (!data.success) {
    throw new Error(data.error || 'API Error');
  }
  return data;
};

export const simulateUbaScenario = async (scenario: string, userId: string = 'jdoe'): Promise<any> => {
  const response = await fetch(`${API_BASE_URL}/simulate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ scenario, user_id: userId }),
  });
  if (!response.ok) {
    throw new Error('Failed to run simulation');
  }
  return response.json();
};
