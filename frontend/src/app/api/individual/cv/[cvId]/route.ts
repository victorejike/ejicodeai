import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../../_client';

export async function GET(
  req: NextRequest,
  { params }: { params: { cvId: string } }
) {
  try {
    const res = await backendFetch(
      `/v1/individual/cv/${encodeURIComponent(params.cvId)}`,
      {},
      req
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Failed to fetch CV' }, { status: 500 });
  }
}
