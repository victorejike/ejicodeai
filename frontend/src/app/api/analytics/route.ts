import { NextResponse } from 'next/server';
import { backendFetch } from '../_client';

export async function GET(req: Request) {
  try {
    const res = await backendFetch('/v1/dashboard/analytics', {}, req);
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({
      opportunity_discovery: [],
      company_growth: [],
      agent_performance: [],
      outreach_success: [],
      revenue_pipeline: [],
      contact_acquisition: [],
      activity_timeline: [],
    }, { status: 500 });
  }
}
