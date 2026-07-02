const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

let _cachedToken: string | null = null;
let _tokenExpiry: number = 0;

async function getToken(): Promise<string | null> {
  const now = Date.now();
  if (_cachedToken && now < _tokenExpiry) return _cachedToken;

  try {
    const res = await fetch(`${API_URL}/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        username: process.env.DEV_USERNAME || 'admin',
        password: process.env.DEV_PASSWORD || 'admin',
      }),
      cache: 'no-store',
    });
    if (!res.ok) return null;
    const data = await res.json();
    _cachedToken = data.access_token || null;
    // Cache for 3.5 hours (token expires in 4h)
    _tokenExpiry = now + 3.5 * 60 * 60 * 1000;
    return _cachedToken;
  } catch {
    return null;
  }
}

export async function backendFetch(path: string, init?: RequestInit) {
  const token = await getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(`${API_URL}${path}`, { ...init, headers, cache: 'no-store' });
}
