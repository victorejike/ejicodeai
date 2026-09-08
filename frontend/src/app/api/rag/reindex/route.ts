import { NextResponse } from 'next/server';
import { backendFetch } from '../../_client';

export async function POST(req: Request) {
  try {
    const res = await backendFetch('/v1/rag/reindex', { method: 'POST' }, req);
    const data = await res.json().catch(() => ({ status: 'reindexed' }));
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json({ error: err?.message || 'Failed to reindex knowledge base' }, { status: 500 });
  }
}
