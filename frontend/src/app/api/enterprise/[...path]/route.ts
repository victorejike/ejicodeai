import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../_client';

async function handleProxy(req: NextRequest, { params }: { params: { path: string[] } }) {
  try {
    const subpath = params.path ? params.path.join('/') : '';
    const search = req.nextUrl.search || '';
    const backendPath = `/v1/enterprise/${subpath}${search}`;

    const headers: Record<string, string> = {};
    const auth = req.headers.get('authorization');
    if (auth) headers['Authorization'] = auth;

    const contentType = req.headers.get('content-type');
    if (contentType) headers['Content-Type'] = contentType;

    let body: any = undefined;
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      body = await req.text();
    }

    const res = await backendFetch(
      backendPath,
      {
        method: req.method,
        headers,
        body,
      },
      req
    );

    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json(
      { error: err?.message || 'Internal proxy error' },
      { status: 500 }
    );
  }
}

export const GET = handleProxy;
export const POST = handleProxy;
export const PUT = handleProxy;
export const PATCH = handleProxy;
export const DELETE = handleProxy;
