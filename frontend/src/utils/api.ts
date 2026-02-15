const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

type RequestOptions = {
  method?: string;
  body?: any;
  token?: string;
};

export async function apiRequest(endpoint: string, options: RequestOptions = {}) {
  const { method = 'GET', body, token } = options;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config: RequestInit = { method, headers };
  if (body) {
    config.body = JSON.stringify(body);
  }

  const url = `${BACKEND_URL}/api${endpoint}`;
  const response = await fetch(url, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}
