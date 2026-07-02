import { NextResponse } from 'next/server';
import { backendFetch } from '../_client';

export async function GET() {
  try {
    const res = await backendFetch('/v1/opportunities?limit=100');
    const data = await res.json();
    return NextResponse.json({ opportunities: data }, { status: res.status });
  } catch {
    return NextResponse.json({ opportunities: [] }, { status: 500 });
  }
}
