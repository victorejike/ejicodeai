import { NextResponse } from 'next/server';
import { backendFetch } from '../_client';

export async function GET(req: Request) {
  try {
    const res = await backendFetch('/v1/opportunities?limit=100', {}, req);
    const data = await res.json();
    return NextResponse.json({ opportunities: data }, { status: res.status });
  } catch {
    return NextResponse.json({ opportunities: [] }, { status: 500 });
  }
}
