import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../_client';

/** Who the caller actually is, resolved from their own bearer token. */
export async function GET(req: NextRequest) {
  try {
    const res = await backendFetch('/v1/auth/me', {}, req);
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Failed to resolve current user' }, { status: 500 });
  }
}
