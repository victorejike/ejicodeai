import { NextResponse } from 'next/server';
import { backendFetch } from '../../../_client';

export async function POST(req: Request, { params }: { params: { proposalId: string } }) {
  try {
    const body = await req.json().catch(() => ({}));
    const reason = body.reason || 'rejected';
    const res = await backendFetch(
      `/v1/proposals/${params.proposalId}/reject?reason=${encodeURIComponent(reason)}`,
      { method: 'PATCH' },
      req
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ detail: 'Reject failed' }, { status: 500 });
  }
}
