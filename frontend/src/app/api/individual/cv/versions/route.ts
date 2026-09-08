import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../../_client';

export async function GET(req: NextRequest) {
  try {
    const limit = new URL(req.url).searchParams.get('limit') ?? '25';
    const res = await backendFetch(`/v1/individual/cv/versions?limit=${encodeURIComponent(limit)}`, {}, req);
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Failed to list CV versions' }, { status: 500 });
  }
}
