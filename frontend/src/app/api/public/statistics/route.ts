import { NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const res = await fetch(`${API_URL}/v1/public/statistics`, { cache: 'no-store' });
    if (!res.ok) {
      throw new Error(`Backend returned status ${res.status}`);
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    // No fabricated numbers: report that live statistics are unavailable so the
    // UI can render an honest empty state instead of fake data.
    return NextResponse.json(
      {
        status: 'unavailable',
        error: err instanceof Error ? err.message : 'Statistics backend is unreachable.',
        data: null,
      },
      { status: 503 }
    );
  }
}
