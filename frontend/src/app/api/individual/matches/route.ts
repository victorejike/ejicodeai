import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../_client';

export async function GET(req: NextRequest) {
  try {
    const authHeader = req.headers.get('authorization');
    const { searchParams } = new URL(req.url);
    const minScore = searchParams.get('min_score') || '50';
    const pipelineType = searchParams.get('pipeline_type') || 'employment';

    const headers: Record<string, string> = {};
    if (authHeader) headers['Authorization'] = authHeader;

    const res = await backendFetch(`/v1/individual/matches?min_score=${minScore}&pipeline_type=${pipelineType}`, {
      headers,
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json({ matches: [], error: 'Failed to fetch matches' }, { status: 500 });
  }
}
