'use client';

import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

type Opportunity = { id: string; title: string; type: string; score: number; status: string; source_platform: string | null; location: string | null };

const badge: Record<string, string> = {
  new: 'bg-blue-900/50 text-vscode-blue border border-blue-700/40',
  researched: 'bg-purple-900/50 text-vscode-purple border border-purple-700/40',
  contacted: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700/40',
  won: 'bg-teal-900/50 text-vscode-green border border-teal-700/40',
  lost: 'bg-red-900/50 text-red-400 border border-red-700/40',
};

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 70 ? 'bg-teal-900/50 text-vscode-green border-teal-700/40' : score >= 40 ? 'bg-yellow-900/50 text-yellow-300 border-yellow-700/40' : 'bg-red-900/50 text-red-400 border-red-700/40';
  return <span className={`rounded px-2 py-0.5 text-[11px] font-semibold border ${color}`}>{score}/100</span>;
}

export default function OpportunitiesPage() {
  const { data, error, isLoading } = useSWR('/api/opportunities', fetcher, {
    fallbackData: { opportunities: [] },
    refreshInterval: 15000,
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-vscode-text">Opportunities</h1>
        <p className="text-vscode-muted text-xs mt-0.5">Discovered and ranked leads from all platforms.</p>
      </div>

      {isLoading && <p className="text-vscode-muted text-xs animate-pulse">Loading opportunities…</p>}
      {error && <p className="text-red-400 text-xs">Failed to load opportunities.</p>}

      {!isLoading && !error && data?.opportunities?.length === 0 && (
        <div className="rounded-lg border border-vscode-border bg-vscode-sidebar p-10 text-center text-vscode-muted">
          <div className="text-3xl mb-3">🎯</div>
          <p className="text-sm font-medium text-vscode-text">No opportunities yet.</p>
          <p className="text-xs mt-1">Trigger the Job Scout agent from the Agents page.</p>
        </div>
      )}

      {data?.opportunities?.length > 0 && (
        <div className="rounded-lg border border-vscode-border bg-vscode-sidebar overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-vscode-border bg-vscode-surface">
                <tr>
                  {['Title', 'Type', 'Platform', 'Score', 'Status'].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-[11px] font-semibold text-vscode-muted uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-vscode-border">
                {data.opportunities.map((o: Opportunity) => (
                  <tr key={o.id} className="hover:bg-vscode-surface transition-colors">
                    <td className="px-4 py-2.5 text-vscode-text max-w-xs truncate font-medium">{o.title}</td>
                    <td className="px-4 py-2.5 text-vscode-muted text-xs">{o.type}</td>
                    <td className="px-4 py-2.5 text-vscode-muted text-xs">{o.source_platform || '—'}</td>
                    <td className="px-4 py-2.5"><ScoreBadge score={o.score ?? 0} /></td>
                    <td className="px-4 py-2.5">
                      <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${badge[o.status] ?? 'bg-vscode-surface text-vscode-muted'}`}>{o.status}</span>
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
