import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../_client';

export async function GET(req: NextRequest) {
  try {
    const authHeader = req.headers.get('authorization');
    const headers: Record<string, string> = {};
    if (authHeader) headers['Authorization'] = authHeader;

    const res = await backendFetch('/v1/individual/rejections', { headers });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json({ rejections: [], error: 'Failed to fetch rejection logs' }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const authHeader = req.headers.get('authorization');
    const body = await req.json();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (authHeader) headers['Authorization'] = authHeader;

    const res = await backendFetch('/v1/individual/rejections', {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json({ error: 'Failed to log rejection' }, { status: 500 });
  }
}
