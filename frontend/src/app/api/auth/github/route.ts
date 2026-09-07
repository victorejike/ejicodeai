import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const accountType = searchParams.get('type') || 'individual';

  try {
    const res = await fetch(`${API_URL}/v1/auth/github/authorize?account_type=${accountType}`, {
      redirect: 'manual',
    });

    // If backend redirected to GitHub
    const location = res.headers.get('location');
    if (location) {
      return NextResponse.redirect(location);
    }

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json(
      { error: err.message || 'Failed to initiate GitHub authentication.' },
      { status: 500 }
    );
  }
}
