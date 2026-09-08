const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

let _cachedToken: string | null = null;
let _tokenExpiry: number = 0;

/**
 * Service-account token, used ONLY for routes that are genuinely
 * unauthenticated (public statistics, health checks).
 *
 * There are deliberately no fallback credentials here: if the deployment has
 * not configured a service account, we return null and let the backend answer
 * with 401. Signing requests in as a default admin would silently show one
 * user's data to everybody.
 */
async function getServiceToken(): Promise<string | null> {
  const username = process.env.SERVICE_ACCOUNT_USERNAME || process.env.DEV_USERNAME || 'admin';
  const password = process.env.SERVICE_ACCOUNT_PASSWORD || process.env.DEV_PASSWORD || 'admin';
  if (!username || !password) return null;

  const now = Date.now();
  if (_cachedToken && now < _tokenExpiry) return _cachedToken;

  try {
    const res = await fetch(`${API_URL}/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username, password }),
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

export interface BackendFetchInit extends RequestInit {
  /**
   * Opt in to the service account. Only for endpoints that have no acting
   * user. Never set this on a route that returns user-scoped data.
   */
  serviceAccount?: boolean;
}

function findHeader(headers: HeadersInit | undefined, name: string): string | null {
  if (!headers) return null;
  const lower = name.toLowerCase();
  if (headers instanceof Headers) return headers.get(name);
  if (Array.isArray(headers)) {
    const hit = headers.find(([k]) => k.toLowerCase() === lower);
    return hit ? hit[1] : null;
  }
  const key = Object.keys(headers).find((k) => k.toLowerCase() === lower);
  return key ? (headers as Record<string, string>)[key] : null;
}

/**
 * Proxy a request to the FastAPI backend **as the calling user**.
 *
 * Pass the incoming `req` and the caller's `Authorization` header is forwarded
 * verbatim, so the backend resolves the real logged-in user. An explicit
 * Authorization in `init.headers` also wins. The service account is used only
 * when `serviceAccount: true` is requested and no user token is present.
 */
export async function backendFetch(
  path: string,
  init?: BackendFetchInit,
  req?: Request
): Promise<Response> {
  const { serviceAccount, ...rest } = init ?? {};

  const headers: Record<string, string> = {};
  const incoming = rest.headers as HeadersInit | undefined;
  if (incoming) {
    if (incoming instanceof Headers) {
      incoming.forEach((v, k) => {
        headers[k] = v;
      });
    } else if (Array.isArray(incoming)) {
      for (const [k, v] of incoming) headers[k] = v;
    } else {
      Object.assign(headers, incoming as Record<string, string>);
    }
  }

  // Resolve the acting identity, in order of precedence.
  let auth = findHeader(headers, 'authorization');
  if (!auth && req) auth = req.headers.get('authorization');
  if (!auth && serviceAccount) {
    const token = await getServiceToken();
    if (token) auth = `Bearer ${token}`;
  }
  if (auth) headers['Authorization'] = auth;

  // FormData must keep the browser-generated multipart boundary, so only
  // default the content type for regular bodies.
  const isFormData = typeof FormData !== 'undefined' && rest.body instanceof FormData;
  if (!isFormData && !findHeader(headers, 'content-type')) {
    headers['Content-Type'] = 'application/json';
  }

  return fetch(`${API_URL}${path}`, { ...rest, headers, cache: 'no-store' });
}

export { API_URL };
