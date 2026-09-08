import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../../../_client';

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ opportunityId: string }> | { opportunityId: string } }
) {
  try {
    const resolvedParams = await params;
    const oppId = encodeURIComponent(resolvedParams.opportunityId);
    const res = await backendFetch(
      `/v1/individual/opportunities/${oppId}/draft-outreach`,
      { method: 'POST' },
      req
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json(
      { error: 'Failed to generate tailored outreach draft', details: err?.message },
      { status: 500 }
    );
  }
}
