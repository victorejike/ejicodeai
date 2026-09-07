import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../_client';

export async function POST(req: NextRequest) {
  try {
    const authHeader = req.headers.get('authorization');
    const headers: Record<string, string> = {};
    if (authHeader) headers['Authorization'] = authHeader;

    const res = await backendFetch('/v1/individual/search', {
      method: 'POST',
      headers,
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json({ error: 'Failed to trigger career search' }, { status: 500 });
  }
}
