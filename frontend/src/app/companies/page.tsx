'use client';

import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

type Company = { id: string; name: string; domain: string | null; industry: string | null; website_url: string | null; fit_score: number; status: string };

const badge: Record<string, string> = {
  discovered: 'bg-blue-900/50 text-vscode-blue border border-blue-700/40',
  researched: 'bg-purple-900/50 text-vscode-purple border border-purple-700/40',
  contacted: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700/40',
  qualified: 'bg-teal-900/50 text-vscode-green border border-teal-700/40',
  disqualified: 'bg-red-900/50 text-red-400 border border-red-700/40',
};

function FitBar({ score }: { score: number }) {
  const color = score >= 70 ? 'bg-vscode-green' : score >= 40 ? 'bg-yellow-400' : 'bg-vscode-red';
  return (
    <div className="mt-3">
      <div className="flex justify-between text-[11px] text-vscode-muted mb-1">
        <span>Fit Score</span>
        <span className="text-vscode-text font-semibold">{score}/100</span>
      </div>
      <div className="h-1 rounded-full bg-vscode-border">
        <div className={`h-1 rounded-full ${color} transition-all`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

export default function CompaniesPage() {
  const { data, error, isLoading } = useSWR('/api/companies', fetcher, {
    fallbackData: { companies: [] },
    refreshInterval: 15000,
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-vscode-text">Companies</h1>
        <p className="text-vscode-muted text-xs mt-0.5">Target companies discovered and tracked by agents.</p>
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="rounded-lg border border-vscode-border bg-vscode-sidebar p-5 animate-pulse">
              <div className="h-3.5 bg-vscode-surface rounded w-3/4 mb-3" />
              <div className="h-2.5 bg-vscode-surface rounded w-1/2 mb-2" />
              <div className="h-2.5 bg-vscode-surface rounded w-1/3" />
            </div>
          ))}
        </div>
      )}

      {error && <div className="rounded border border-red-700/40 bg-red-900/30 px-4 py-3 text-xs text-red-400">Failed to load companies.</div>}

      {!isLoading && !error && data?.companies?.length === 0 && (
        <div className="rounded-lg border border-vscode-border bg-vscode-sidebar p-10 text-center text-vscode-muted">
          <div className="text-3xl mb-3">🏢</div>
          <p className="text-sm font-medium text-vscode-text">No companies yet.</p>
          <p className="text-xs mt-1">Trigger the Company Scout agent to discover targets.</p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {data?.companies?.map((c: Company) => (
          <div key={c.id} className="rounded-lg border border-vscode-border bg-vscode-sidebar p-4 hover:border-vscode-accent/50 hover:bg-vscode-surface transition-all">
            <div className="flex items-start justify-between gap-2 mb-2">
              <h2 className="font-medium text-vscode-text text-sm truncate">{c.name}</h2>
              <span className={`shrink-0 rounded px-2 py-0.5 text-[11px] font-medium ${badge[c.status] ?? 'bg-vscode-surface text-vscode-muted'}`}>{c.status}</span>
            </div>
            {c.domain && (
              <a href={`https://${c.domain}`} target="_blank" rel="noopener noreferrer" className="text-[11px] text-vscode-blue hover:underline">{c.domain}</a>
            )}
            {c.industry && <p className="text-[11px] text-vscode-muted mt-1">{c.industry}</p>}
            <FitBar score={c.fit_score ?? 0} />
          </div>
        ))}
      </div>
    </div>
  );
}
