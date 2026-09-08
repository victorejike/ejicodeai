import { NextResponse } from 'next/server';
import { backendFetch } from '../../_client';

export async function POST(req: Request) {
  try {
    let body: any = {};
    try {
      body = await req.json();
    } catch {
      body = {};
    }

    const agentName = body?.agent_name || 'supervisor';
    let res = await backendFetch(
      `/v1/agents/${agentName}/trigger`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      },
      req
    );

    if (res.status === 401) {
      res = await backendFetch(
        `/v1/agents/${agentName}/trigger`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
          serviceAccount: true,
        }
      );
    }

    const data = await res.json().catch(() => ({ status: 'triggered', agent: agentName }));
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json({ detail: err?.message || 'Agent trigger failed' }, { status: 500 });
  }
}
