import { NextResponse } from 'next/server';
import { backendFetch } from '../../../_client';

export async function POST(req: Request, { params }: { params: { agentName: string } }) {
  try {
    const res = await backendFetch(`/v1/agents/${params.agentName}/trigger`, { method: 'POST' });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ detail: 'Trigger failed' }, { status: 500 });
  }
}
