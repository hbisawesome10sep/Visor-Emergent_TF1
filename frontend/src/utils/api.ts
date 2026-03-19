const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

type RequestOptions = {
  method?: string;
  body?: any;
  token?: string;
  isFormData?: boolean;
};

// Global logout callback — set by AuthContext so apiRequest can trigger auto-logout
let _onTokenExpired: (() => void) | null = null;
export function setTokenExpiredHandler(handler: () => void) {
  _onTokenExpired = handler;
}

export async function apiRequest(endpoint: string, options: RequestOptions = {}) {
  const { method = 'GET', body, token, isFormData } = options;
  const headers: Record<string, string> = {};
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config: RequestInit = { method, headers };
  if (body) {
    config.body = isFormData ? body : JSON.stringify(body);
  }

  const url = `${BACKEND_URL}/api${endpoint}`;
  const response = await fetch(url, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    // Auto-logout on token expiration
    if (response.status === 401 && _onTokenExpired) {
      _onTokenExpired();
    }
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}
