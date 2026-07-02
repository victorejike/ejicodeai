import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function POST(req: NextRequest) {
  const { username, password } = await req.json();
  const res = await fetch(`${API_URL}/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username, password }),
  });
  const data = await res.json();
  if (!res.ok) return NextResponse.json({ error: data.detail || 'Login failed' }, { status: 401 });
  return NextResponse.json(data);
}
