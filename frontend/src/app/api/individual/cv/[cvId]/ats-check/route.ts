import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../../../_client';

/** Re-score a stored CV, optionally against a different target job. */
export async function POST(
  req: NextRequest,
  { params }: { params: { cvId: string } }
) {
  try {
    const opportunityId = new URL(req.url).searchParams.get('opportunity_id');
    const query = opportunityId ? `?opportunity_id=${encodeURIComponent(opportunityId)}` : '';
    const res = await backendFetch(
      `/v1/individual/cv/${encodeURIComponent(params.cvId)}/ats-check${query}`,
      { method: 'POST' },
      req
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Failed to re-check ATS score' }, { status: 500 });
  }
}
