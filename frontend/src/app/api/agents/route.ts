import { NextResponse } from 'next/server';
import { backendFetch } from '../_client';

export async function GET() {
  try {
    const [statusRes, runsRes] = await Promise.all([
      backendFetch('/v1/agents/status'),
      backendFetch('/v1/agents/runs?limit=50'),
    ]);
    const agentStatus = await statusRes.json();
    const runs = await runsRes.json();
    return NextResponse.json({ agents: agentStatus, runs });
  } catch {
    return NextResponse.json({ agents: [], runs: [] }, { status: 500 });
  }
}
