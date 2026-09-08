'use client';

/**
 * One client for every call the browser makes to our own `/api/*` proxy routes.
 *
 * Two things every page needed and kept re-implementing:
 *   - attach the logged-in user's bearer token (so the backend resolves *them*,
 *     not a service account),
 *   - surface the HTTP status, because 428 "profile incomplete" is a normal,
 *     actionable answer that the UI has to render rather than swallow.
 */

export interface MissingField {
  key: string;
  label: string;
  weight: number;
  hint: string;
  required_for_agents: boolean;
  partially_complete: boolean;
}

export interface ProfileCompletion {
  percent: number;
  threshold: number;
  has_cv: boolean;
  cv_required: boolean;
  is_complete: boolean;
  agent_ready: boolean;
  missing_fields: MissingField[];
  blocking_fields: MissingField[];
  reasons: string[];
  display_name: string | null;
  first_name: string | null;
}

/** HTTP 428 Precondition Required - the account is not ready, the request was fine. */
export const PROFILE_GATE_STATUS = 428;

export class ApiError extends Error {
  readonly status: number;
  readonly payload: any;

  constructor(status: number, message: string, payload: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }

  /** True when the backend refused because the profile is not complete enough. */
  get isProfileGate(): boolean {
    return this.status === PROFILE_GATE_STATUS;
  }

  get profileCompletion(): ProfileCompletion | null {
    const detail = this.payload?.detail ?? this.payload;
    return detail?.profile_completion ?? null;
  }

  get missingFields(): MissingField[] {
    return this.profileCompletion?.missing_fields ?? [];
  }
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('token');
}

export function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...(extra ?? {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

function messageFrom(payload: any, status: number): string {
  const detail = payload?.detail;
  if (typeof detail === 'string') return detail;
  if (detail?.message) return detail.message;
  if (typeof payload?.error === 'string') return payload.error;
  if (typeof payload?.message === 'string') return payload.message;
  return `Request failed (${status})`;
}

/** Raw response, token attached. Use when you need headers or a binary body. */
export async function apiRaw(path: string, init: RequestInit = {}): Promise<Response> {
  const isForm = typeof FormData !== 'undefined' && init.body instanceof FormData;
  const headers = authHeaders(
    isForm ? undefined : { 'Content-Type': 'application/json', ...(init.headers as any) }
  );
  if (isForm && init.headers) Object.assign(headers, init.headers as any);
  return fetch(path, { ...init, headers, cache: 'no-store' });
}

/** JSON call that throws `ApiError` (carrying `status`) on any non-2xx. */
export async function apiFetch<T = any>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await apiRaw(path, init);

  let payload: any = null;
  const text = await res.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { message: text };
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, messageFrom(payload, res.status), payload);
  }
  return payload as T;
}

export function apiPost<T = any>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export function apiPut<T = any>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: 'PUT',
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

/** SWR fetcher. Same error type, so `error.status` is always available. */
export const fetcher = <T = any>(path: string) => apiFetch<T>(path);

/**
 * Trigger a browser download for an authenticated endpoint.
 *
 * A plain `<a href>` cannot carry the bearer token, so the bytes are fetched and
 * handed to an object URL. The server-sent filename is honoured.
 */
export async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const res = await apiRaw(path);
  if (!res.ok) {
    let payload: any = null;
    try {
      payload = await res.json();
    } catch {
      /* body was not JSON */
    }
    throw new ApiError(res.status, messageFrom(payload, res.status), payload);
  }

  const disposition = res.headers.get('content-disposition') || '';
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = match?.[1] || fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
