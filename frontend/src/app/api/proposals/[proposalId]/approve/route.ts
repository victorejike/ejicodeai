import { NextResponse } from 'next/server';
import { backendFetch } from '../../../_client';

export async function POST(req: Request, { params }: { params: { proposalId: string } }) {
  try {
    const res = await backendFetch(
      `/v1/proposals/${params.proposalId}/approve`,
      { method: 'PATCH' },
      req
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ detail: 'Approve failed' }, { status: 500 });
  }
}
