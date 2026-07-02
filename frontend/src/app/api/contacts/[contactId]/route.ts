import { NextResponse } from 'next/server';
import { backendFetch } from '../../_client';

export async function GET(req: Request, { params }: { params: { contactId: string } }) {
  try {
    const res = await backendFetch(`/v1/contacts/${params.contactId}`);
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ detail: 'Not found' }, { status: 404 });
  }
}
