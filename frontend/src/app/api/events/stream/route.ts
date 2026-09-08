import { NextRequest } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const backendUrl = `${API_URL}/v1/events/stream?${searchParams.toString()}`;

  // Forward the caller's identity so the backend can scope the stream to this
  // user's own agent activity. EventSource cannot set headers, so the token may
  // also arrive as an `access_token` query param.
  const headers: Record<string, string> = { Accept: 'text/event-stream' };
  const authHeader = req.headers.get('authorization');
  const queryToken = searchParams.get('access_token');
  if (authHeader) headers['Authorization'] = authHeader;
  else if (queryToken) headers['Authorization'] = `Bearer ${queryToken}`;

  try {
    const response = await fetch(backendUrl, { headers, cache: 'no-store' });

    return new Response(response.body, {
      status: response.status,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        Connection: 'keep-alive',
        'X-Accel-Buffering': 'no',
      },
    });
  } catch (err) {
    return new Response('Event stream unavailable', { status: 502 });
  }
}
