import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../_client';

export async function GET(req: NextRequest) {
  try {
    const authHeader = req.headers.get('authorization');
    const headers: Record<string, string> = {};
    if (authHeader) headers['Authorization'] = authHeader;

    const res = await backendFetch('/v1/individual/companies-to-approach', { headers });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json({ companies: [], error: 'Failed to fetch proactive company targets' }, { status: 500 });
  }
}
