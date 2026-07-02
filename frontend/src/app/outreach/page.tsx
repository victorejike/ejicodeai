'use client';

import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

type OutreachRecord = { id: string; delivery_status: string; message_id: string; open_count: number; opened_at: string | null; replied_at: string | null; follow_up_sequence_step: number; outcome: string | null; proposal_id: string; contact_id: string };

const badge: Record<string, string> = {
  pending: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700/40',
  delivered: 'bg-blue-900/50 text-vscode-blue border border-blue-700/40',
  replied: 'bg-teal-900/50 text-vscode-green border border-teal-700/40',
  failed: 'bg-red-900/50 text-red-400 border border-red-700/40',
};

const outcomeColor: Record<string, string> = {
  INTERESTED: 'text-vscode-green',
  NOT_INTERESTED: 'text-red-400',
  REQUEST_INFO: 'text-vscode-blue',
  AUTO_REPLY: 'text-vscode-muted',
  BOUNCE: 'text-red-400',
};

export default function OutreachPage() {
  const { data, error, isLoading } = useSWR('/api/outreach', fetcher, {
    refreshInterval: 15000,
    fallbackData: { outreach: [] },
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-vscode-text">Outreach History</h1>
        <p className="text-vscode-muted text-xs mt-0.5">Track sent emails, opens, replies, and follow-ups · refreshes every 15s</p>
      </div>

      {isLoading && <p className="text-vscode-muted text-xs animate-pulse">Loading outreach history…</p>}
      {error && <p className="text-red-400 text-xs">Failed to load outreach history.</p>}

      {!isLoading && !error && data?.outreach?.length === 0 && (
        <div className="rounded-lg border border-vscode-border bg-vscode-sidebar p-10 text-center text-vscode-muted">
          <div className="text-3xl mb-3">📧</div>
          <p className="text-sm font-medium text-vscode-text">No outreach sent yet.</p>
          <p className="text-xs mt-1">Approve a proposal then send it via the API.</p>
        </div>
      )}

      {data?.outreach?.length > 0 && (
        <div className="rounded-lg border border-vscode-border bg-vscode-sidebar overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-vscode-border bg-vscode-surface">
                <tr>
                  {['Status', 'Opens', 'Opened At', 'Replied At', 'Follow-up Step', 'Outcome'].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-[11px] font-semibold text-vscode-muted uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-vscode-border">
                {data.outreach.map((o: OutreachRecord) => (
                  <tr key={o.id} className="hover:bg-vscode-surface transition-colors">
                    <td className="px-4 py-2.5">
                      <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${badge[o.delivery_status] ?? 'bg-vscode-surface text-vscode-muted'}`}>{o.delivery_status}</span>
                    </td>
                    <td className="px-4 py-2.5 text-vscode-text">{o.open_count}</td>
                    <td className="px-4 py-2.5 text-vscode-muted text-xs">{o.opened_at ? new Date(o.opened_at).toLocaleDateString() : '—'}</td>
                    <td className="px-4 py-2.5 text-vscode-muted text-xs">{o.replied_at ? new Date(o.replied_at).toLocaleDateString() : '—'}</td>
                    <td className="px-4 py-2.5 text-vscode-text">{o.follow_up_sequence_step}</td>
                    <td className={`px-4 py-2.5 text-xs font-medium ${outcomeColor[o.outcome ?? ''] ?? 'text-vscode-muted'}`}>{o.outcome || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
