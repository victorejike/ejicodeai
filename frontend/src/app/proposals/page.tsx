'use client';

import useSWR from 'swr';
import { useState } from 'react';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

type Proposal = { id: string; status: string; subject: string | null; body: string | null; type: string | null; tone: string | null; word_count: number | null; opportunity_id: string | null; contact_id: string | null };

const badge: Record<string, string> = {
  draft: 'bg-vscode-surface text-vscode-muted border border-vscode-border',
  approved: 'bg-teal-900/50 text-vscode-green border border-teal-700/40',
  rejected: 'bg-red-900/50 text-red-400 border border-red-700/40',
  sent: 'bg-blue-900/50 text-vscode-blue border border-blue-700/40',
};

function Modal({ proposal, onClose }: { proposal: Proposal; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60" onClick={onClose}>
      <div className="bg-vscode-sidebar border border-vscode-border rounded-lg w-full max-w-2xl max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="px-5 py-3.5 border-b border-vscode-border flex items-center justify-between">
          <h2 className="font-medium text-vscode-text text-sm truncate">{proposal.subject || '(No subject)'}</h2>
          <button onClick={onClose} className="text-vscode-muted hover:text-vscode-text text-lg leading-none ml-4">×</button>
        </div>
        <div className="px-5 py-4 overflow-y-auto text-sm text-vscode-text whitespace-pre-wrap leading-relaxed font-mono text-xs">
          {proposal.body || 'No body content.'}
        </div>
      </div>
    </div>
  );
}

export default function ProposalsPage() {
  const { data, error, isLoading, mutate } = useSWR('/api/proposals', fetcher, { fallbackData: { proposals: [] } });
  const [preview, setPreview] = useState<Proposal | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const handleAction = async (id: string, action: 'approve' | 'reject') => {
    setBusy(id + action);
    try {
      const endpoint = action === 'approve' ? `/api/proposals/${id}/approve` : `/api/proposals/${id}/reject`;
      const body = action === 'reject' ? JSON.stringify({ reason: 'rejected' }) : undefined;
      await fetch(endpoint, { method: 'POST', headers: body ? { 'Content-Type': 'application/json' } : undefined, body });
      await mutate();
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      {preview && <Modal proposal={preview} onClose={() => setPreview(null)} />}

      <div className="mb-6">
        <h1 className="text-xl font-semibold text-vscode-text">Proposals</h1>
        <p className="text-vscode-muted text-xs mt-0.5">AI-generated outreach proposals awaiting human review.</p>
      </div>

      {isLoading && <p className="text-vscode-muted text-xs animate-pulse">Loading proposals…</p>}
      {error && <p className="text-red-400 text-xs">Failed to load proposals.</p>}

      {!isLoading && !error && data?.proposals?.length === 0 && (
        <div className="rounded-lg border border-vscode-border bg-vscode-sidebar p-10 text-center text-vscode-muted">
          <div className="text-3xl mb-3">📄</div>
          <p className="text-sm font-medium text-vscode-text">No proposals yet.</p>
          <p className="text-xs mt-1">Generate one via the API after discovering opportunities and contacts.</p>
        </div>
      )}

      <div className="space-y-2.5">
        {data?.proposals?.map((p: Proposal) => (
          <div key={p.id} className="rounded-lg border border-vscode-border bg-vscode-sidebar p-4 hover:border-vscode-accent/50 transition-colors">
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className="flex-1 min-w-0">
                <button onClick={() => setPreview(p)} className="font-medium text-vscode-text text-sm hover:text-vscode-blue text-left truncate block w-full transition-colors">
                  {p.subject || '(No subject)'}
                </button>
                <p className="text-[11px] text-vscode-muted mt-0.5">
                  {[p.type, p.tone, p.word_count ? `${p.word_count} words` : null].filter(Boolean).join(' · ')}
                </p>
              </div>
              <span className={`shrink-0 rounded px-2 py-0.5 text-[11px] font-medium ${badge[p.status] ?? 'bg-vscode-surface text-vscode-muted'}`}>{p.status}</span>
            </div>
            {p.body && <p className="text-[11px] text-vscode-muted line-clamp-2 mb-3 font-mono">{p.body}</p>}
            <div className="flex flex-wrap gap-2">
              <button onClick={() => setPreview(p)} className="rounded border border-vscode-border px-3 py-1 text-xs text-vscode-muted hover:text-vscode-text hover:bg-vscode-surface transition-colors">
                Preview
              </button>
              {p.status === 'draft' && (
                <>
                  <button disabled={!!busy} onClick={() => handleAction(p.id, 'approve')} className="rounded bg-teal-700 hover:bg-teal-600 disabled:opacity-50 px-3 py-1 text-xs font-medium text-white transition-colors">
                    {busy === p.id + 'approve' ? 'Approving…' : '✓ Approve'}
                  </button>
                  <button disabled={!!busy} onClick={() => handleAction(p.id, 'reject')} className="rounded bg-red-900/50 hover:bg-red-900 border border-red-700/40 disabled:opacity-50 px-3 py-1 text-xs font-medium text-red-400 transition-colors">
                    {busy === p.id + 'reject' ? 'Rejecting…' : '✕ Reject'}
                  </button>
                </>
              )}
              {p.status === 'approved' && <span className="text-xs text-vscode-green font-medium self-center">✓ Ready to send</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
