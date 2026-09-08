import { NextResponse } from 'next/server';
import { backendFetch } from '../_client';

export async function GET(req: Request) {
  try {
    const res = await backendFetch('/v1/outreach?limit=100', {}, req);
    const text = await res.text();
    if (!text) {
      return NextResponse.json({ outreach: [] }, { status: res.status });
    }
    const data = JSON.parse(text);
    return NextResponse.json({ outreach: Array.isArray(data) ? data : [] }, { status: res.status });
  } catch {
    return NextResponse.json({ outreach: [] }, { status: 500 });
  }
}
