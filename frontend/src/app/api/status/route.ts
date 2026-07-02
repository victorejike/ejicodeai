import { NextResponse } from 'next/server';
import { backendFetch } from '../_client';

export async function GET() {
  try {
    const res = await backendFetch('/v1/dashboard/summary');
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ status: 'error', counts: {}, latest_opportunities: [], recent_agent_runs: [] }, { status: 500 });
  }
}
