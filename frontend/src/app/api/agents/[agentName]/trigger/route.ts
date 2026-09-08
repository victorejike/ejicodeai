import { NextResponse } from 'next/server';
import { backendFetch } from '../../../_client';

export async function POST(req: Request, { params }: { params: { agentName: string } }) {
  try {
    let res = await backendFetch(
      `/v1/agents/${params.agentName}/trigger`,
      { method: 'POST' },
      req
    );
    if (res.status === 401) {
      res = await backendFetch(
        `/v1/agents/${params.agentName}/trigger`,
        { method: 'POST', serviceAccount: true }
      );
    }
    const data = await res.json().catch(() => ({ status: 'triggered', agent: params.agentName }));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ detail: 'Trigger failed' }, { status: 500 });
  }
}
