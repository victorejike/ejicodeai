import { NextRequest } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const backendUrl = `${API_URL}/v1/events/stream?${searchParams.toString()}`;

  try {
    const response = await fetch(backendUrl, {
      headers: {
        Accept: 'text/event-stream',
      },
      cache: 'no-store',
    });

    return new Response(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        Connection: 'keep-alive',
      },
    });
  } catch (err) {
    return new Response('Event stream unavailable', { status: 502 });
  }
}
