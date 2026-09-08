import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../../_client';

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();

    const backendRes = await backendFetch(
      '/v1/individual/profile/avatar',
      { method: 'POST', body: formData },
      req
    );

    const data = await backendRes.json();
    return NextResponse.json(data, { status: backendRes.status });
  } catch (err: any) {
    return NextResponse.json(
      { error: 'Failed to upload avatar', details: err?.message },
      { status: 500 }
    );
  }
}
