import { NextResponse } from 'next/server';
import { backendFetch } from '../_client';

export async function GET(req: Request) {
  try {
    let [statusRes, runsRes] = await Promise.all([
      backendFetch('/v1/agents/status', {}, req),
      backendFetch('/v1/agents/runs?limit=50', {}, req),
    ]);

    // If unauthenticated or token expired, retry using service account for platform health
    if (!statusRes.ok) {
      statusRes = await backendFetch('/v1/agents/status', { serviceAccount: true });
    }
    if (!runsRes.ok) {
      runsRes = await backendFetch('/v1/agents/runs?limit=50', { serviceAccount: true });
    }

    const agentStatus = statusRes.ok ? await statusRes.json().catch(() => []) : [];
    const runs = runsRes.ok ? await runsRes.json().catch(() => []) : [];

    return NextResponse.json({
      agents: Array.isArray(agentStatus) ? agentStatus : [],
      runs: Array.isArray(runs) ? runs : [],
    });
  } catch {
    return NextResponse.json({ agents: [], runs: [] });
  }
}
