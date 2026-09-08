import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../_client';

/** This user's recent pipeline runs plus the declared stage list. */
export async function GET(req: NextRequest) {
  try {
    const limit = new URL(req.url).searchParams.get('limit') ?? '10';
    const res = await backendFetch(
      `/v1/individual/pipeline?limit=${encodeURIComponent(limit)}`,
      {},
      req
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Failed to fetch pipeline runs' }, { status: 500 });
  }
}
