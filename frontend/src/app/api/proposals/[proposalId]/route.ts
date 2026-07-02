import { NextResponse } from 'next/server';
import { backendFetch } from '../../_client';

export async function POST(req: Request, { params }: { params: { proposalId: string } }) {
  const url = new URL(req.url);
  const action = url.pathname.split('/').pop(); // 'approve' or 'reject'
  try {
    const res = await backendFetch(`/v1/proposals/${params.proposalId}/${action}`, { method: 'PATCH' });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ detail: 'Action failed' }, { status: 500 });
  }
}
