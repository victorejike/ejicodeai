import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getAuthToken(): Promise<string | null> {
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
    return data.access_token || null;
  } catch {
    return null;
  }
}

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();

    // Always use the real logged-in user's session token so the CV attaches to
    // their own account. Only fall back to a dev auto-login when there is no
    // real session at all (local testing without being signed in).
    const authHeader = req.headers.get('authorization');
    const token = authHeader ? authHeader.replace(/^Bearer\s+/i, '') : await getAuthToken();

    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const backendRes = await fetch(`${API_URL}/v1/individual/cv/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    const data = await backendRes.json();
    return NextResponse.json(data, { status: backendRes.status });
  } catch (err: any) {
    return NextResponse.json(
      { error: 'Failed to upload and parse CV', details: err?.message },
      { status: 500 }
    );
  }
}
