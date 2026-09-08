import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../../_client';

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();

    // The CV must attach to the real logged-in user, so the caller's bearer
    // token is forwarded as-is. There is no dev auto-login fallback: without a
    // session the backend answers 401 and the UI asks the user to sign in.
    const backendRes = await backendFetch(
      '/v1/individual/cv/upload',
      { method: 'POST', body: formData },
      req
    );

    const data = await backendRes.json();
    return NextResponse.json(data, { status: backendRes.status });
  } catch (err: any) {
    return NextResponse.json(
      { error: 'Failed to upload and parse CV', details: err?.message },
      { status: 500 }
    );
  }
}
