import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../../_client';

/** Stage-by-stage status of one run, polled by the progress view. */
export async function GET(
  req: NextRequest,
  { params }: { params: { executionId: string } }
) {
  try {
    const res = await backendFetch(
      `/v1/individual/pipeline/${encodeURIComponent(params.executionId)}`,
      {},
      req
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Failed to fetch pipeline run' }, { status: 500 });
  }
}
