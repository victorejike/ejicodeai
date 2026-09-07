import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../_client';

export async function GET(req: NextRequest) {
  try {
    const authHeader = req.headers.get('authorization');
    const headers: Record<string, string> = {};
    if (authHeader) headers['Authorization'] = authHeader;

    const res = await backendFetch('/v1/individual/search-config', { headers });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json({ error: 'Failed to fetch continuous search config' }, { status: 500 });
  }
}

export async function PUT(req: NextRequest) {
  try {
    const authHeader = req.headers.get('authorization');
    const body = await req.json();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (authHeader) headers['Authorization'] = authHeader;

    const res = await backendFetch('/v1/individual/search-config', {
      method: 'PUT',
      headers,
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json({ error: 'Failed to update continuous search config' }, { status: 500 });
  }
}
