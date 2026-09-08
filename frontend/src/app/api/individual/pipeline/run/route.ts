import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../../_client';

/**
 * Start the agent chain for the calling user.
 *
 * A 428 here is the profile gate, and its body carries the missing-field list,
 * so it is passed through verbatim rather than flattened into a generic error.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const res = await backendFetch(
      '/v1/individual/pipeline/run',
      { method: 'POST', body: JSON.stringify(body) },
      req
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Failed to start the agent pipeline' }, { status: 500 });
  }
}
