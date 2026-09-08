import { NextRequest, NextResponse } from 'next/server';
import { backendFetch } from '../../../../_client';

/**
 * Stream a rendered CV back to the browser.
 *
 * The body is binary for `.docx`/`.pdf`, so it is passed through untouched -
 * re-encoding it as JSON would corrupt the document. The backend's own
 * `Content-Disposition` (which carries the filename) is preserved.
 */
export async function GET(
  req: NextRequest,
  { params }: { params: { cvId: string } }
) {
  try {
    const format = new URL(req.url).searchParams.get('format') ?? 'pdf';
    const res = await backendFetch(
      `/v1/individual/cv/${encodeURIComponent(params.cvId)}/download?format=${encodeURIComponent(format)}`,
      {},
      req
    );

    if (!res.ok) {
      const text = await res.text();
      return new NextResponse(text, {
        status: res.status,
        headers: { 'Content-Type': res.headers.get('content-type') ?? 'application/json' },
      });
    }

    const body = await res.arrayBuffer();
    const headers = new Headers();
    headers.set('Content-Type', res.headers.get('content-type') ?? 'application/octet-stream');
    const disposition = res.headers.get('content-disposition');
    if (disposition) headers.set('Content-Disposition', disposition);

    return new NextResponse(body, { status: 200, headers });
  } catch {
    return NextResponse.json({ error: 'Failed to download CV' }, { status: 500 });
  }
}
