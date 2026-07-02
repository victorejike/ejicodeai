'use client';

import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

type Contact = { id: string; email: string; full_name: string | null; title: string | null; is_decision_maker: boolean; email_confidence: string; status: string };

const confBadge: Record<string, string> = {
  verified: 'bg-teal-900/50 text-vscode-green border border-teal-700/40',
  probable: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700/40',
  unverified: 'bg-vscode-surface text-vscode-muted border border-vscode-border',
};

export default function ContactsPage() {
  const { data, error, isLoading } = useSWR('/api/contacts', fetcher, {
    fallbackData: { contacts: [] },
    refreshInterval: 15000,
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-vscode-text">Contacts</h1>
        <p className="text-vscode-muted text-xs mt-0.5">Decision makers and contacts discovered by agents.</p>
      </div>

      {isLoading && <p className="text-vscode-muted text-xs animate-pulse">Loading contacts…</p>}
      {error && <p className="text-red-400 text-xs">Failed to load contacts.</p>}

      {!isLoading && !error && data?.contacts?.length === 0 && (
        <div className="rounded-lg border border-vscode-border bg-vscode-sidebar p-10 text-center text-vscode-muted">
          <div className="text-3xl mb-3">👤</div>
          <p className="text-sm font-medium text-vscode-text">No contacts yet.</p>
          <p className="text-xs mt-1">Run the Contact Discovery agent to find decision makers.</p>
        </div>
      )}

      {data?.contacts?.length > 0 && (
        <div className="rounded-lg border border-vscode-border bg-vscode-sidebar overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-vscode-border bg-vscode-surface">
                <tr>
                  {['Name', 'Email', 'Title', 'Confidence', 'Decision Maker'].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-[11px] font-semibold text-vscode-muted uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-vscode-border">
                {data.contacts.map((c: Contact) => (
                  <tr key={c.id} className="hover:bg-vscode-surface transition-colors">
                    <td className="px-4 py-2.5 text-vscode-text font-medium">{c.full_name || '—'}</td>
                    <td className="px-4 py-2.5 text-vscode-blue text-xs">{c.email}</td>
                    <td className="px-4 py-2.5 text-vscode-muted text-xs">{c.title || '—'}</td>
                    <td className="px-4 py-2.5">
                      <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${confBadge[c.email_confidence] ?? 'bg-vscode-surface text-vscode-muted'}`}>{c.email_confidence}</span>
                    </td>
                    <td className="px-4 py-2.5">
                      {c.is_decision_maker
                        ? <span className="rounded px-2 py-0.5 text-[11px] font-medium bg-vscode-accent text-white">Yes</span>
                        : <span className="text-vscode-muted">—</span>}
                    </td>
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
