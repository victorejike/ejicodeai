import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../_client';

export async function GET(req: NextRequest) {
  try {
    const authHeader = req.headers.get('authorization');
    const headers: Record<string, string> = {};
    if (authHeader) headers['Authorization'] = authHeader;

    const res = await backendFetch('/v1/individual/dashboard-stats', { headers });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json({ error: 'Failed to fetch individual dashboard stats' }, { status: 500 });
  }
}
