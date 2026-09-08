import { NextResponse } from 'next/server';
import { backendFetch } from '../_client';

export async function GET(req: Request) {
  try {
    const res = await backendFetch('/v1/proposals?limit=100', {}, req);
    const text = await res.text();
    if (!text) {
      return NextResponse.json({ proposals: [] }, { status: res.status });
    }
    const data = JSON.parse(text);
    return NextResponse.json({ proposals: Array.isArray(data) ? data : [] }, { status: res.status });
  } catch {
    return NextResponse.json({ proposals: [] }, { status: 500 });
  }
}
