'use client';

import useSWR from 'swr';
import Link from 'next/link';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

const dotColor: Record<string, string> = {
  ok: 'bg-vscode-green',
  degraded: 'bg-yellow-400',
  error: 'bg-vscode-red',
  loading: 'bg-vscode-muted',
};

const runBadge: Record<string, string> = {
  running: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700/40',
  success: 'bg-teal-900/50 text-vscode-green border border-teal-700/40',
  completed: 'bg-teal-900/50 text-vscode-green border border-teal-700/40',
  failure: 'bg-red-900/50 text-red-400 border border-red-700/40',
  escalated: 'bg-orange-900/50 text-orange-300 border border-orange-700/40',
};

const oppBadge: Record<string, string> = {
  new: 'bg-blue-900/50 text-vscode-blue border border-blue-700/40',
  researched: 'bg-purple-900/50 text-vscode-purple border border-purple-700/40',
  contacted: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700/40',
  won: 'bg-teal-900/50 text-vscode-green border border-teal-700/40',
  lost: 'bg-red-900/50 text-red-400 border border-red-700/40',
};

const stats = [
  { key: 'companies', label: 'Companies', href: '/companies', icon: '🏢' },
  { key: 'opportunities', label: 'Opportunities', href: '/opportunities', icon: '🎯' },
  { key: 'proposals', label: 'Proposals', href: '/proposals', icon: '📄' },
  { key: 'outreach_history', label: 'Outreach Sent', href: '/outreach', icon: '📧' },
  { key: 'active_agents', label: 'Active Agents', href: '/agents', icon: '🤖' },
  { key: 'reports', label: 'Reports', href: '/agents', icon: '📊' },
];

export default function Dashboard() {
  const { data, error, isLoading } = useSWR('/api/status', fetcher, {
    refreshInterval: 10000,
    fallbackData: {
      status: 'loading',
      counts: { companies: 0, opportunities: 0, proposals: 0, outreach_history: 0, reports: 0, active_agents: 0 },
      latest_opportunities: [],
      recent_agent_runs: [],
    },
  });

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-vscode-text">Dashboard</h1>
          <p className="text-vscode-muted text-xs mt-0.5">Real-time overview · auto-refreshes every 10s</p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className={`inline-block w-2 h-2 rounded-full ${dotColor[data?.status] ?? 'bg-vscode-muted'}`} />
          <span className="text-vscode-muted capitalize">{isLoading ? 'Connecting…' : data?.status ?? 'unknown'}</span>
        </div>
      </div>

      {error && (
        <div className="mb-5 rounded border border-red-700/40 bg-red-900/30 px-4 py-3 text-xs text-red-400">
          ⚠ Cannot reach backend. Make sure the API is running on port 8000.
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        {stats.map(({ key, label, href, icon }) => (
          <Link key={key} href={href}
            className="rounded-lg border border-vscode-border bg-vscode-sidebar p-4 hover:border-vscode-accent/60 hover:bg-vscode-surface transition-all group">
            <div className="text-lg mb-1">{icon}</div>
            <div className="text-2xl font-bold text-vscode-text group-hover:text-vscode-blue transition-colors">
              {isLoading ? '—' : (data?.counts?.[key as keyof typeof data.counts] ?? 0)}
            </div>
            <div className="text-[11px] text-vscode-muted mt-0.5">{label}</div>
          </Link>
        ))}
      </div>

      {/* Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Recent Opportunities */}
        <div className="rounded-lg border border-vscode-border bg-vscode-sidebar overflow-hidden">
          <div className="px-4 py-3 border-b border-vscode-border flex items-center justify-between">
            <h2 className="text-sm font-medium text-vscode-text">Recent Opportunities</h2>
            <Link href="/opportunities" className="text-[11px] text-vscode-muted hover:text-vscode-blue transition-colors">View all →</Link>
          </div>
          <div className="divide-y divide-vscode-border">
            {data?.latest_opportunities?.length ? (
              data.latest_opportunities.map((o: any) => (
                <div key={o.id} className="px-4 py-2.5 flex items-center justify-between gap-3 hover:bg-vscode-surface transition-colors">
                  <p className="text-sm text-vscode-text truncate">{o.title}</p>
                  <span className={`shrink-0 rounded px-2 py-0.5 text-[11px] font-medium ${oppBadge[o.status] ?? 'bg-vscode-surface text-vscode-muted'}`}>
                    {o.status}
                  </span>
                </div>
              ))
            ) : (
              <p className="px-4 py-6 text-xs text-vscode-muted text-center">No opportunities yet — trigger the Job Scout agent.</p>
            )}
          </div>
        </div>

        {/* Recent Agent Runs */}
        <div className="rounded-lg border border-vscode-border bg-vscode-sidebar overflow-hidden">
          <div className="px-4 py-3 border-b border-vscode-border flex items-center justify-between">
            <h2 className="text-sm font-medium text-vscode-text">Recent Agent Runs</h2>
            <Link href="/agents" className="text-[11px] text-vscode-muted hover:text-vscode-blue transition-colors">View all →</Link>
          </div>
          <div className="divide-y divide-vscode-border">
            {data?.recent_agent_runs?.length ? (
              data.recent_agent_runs.map((run: any, i: number) => (
                <div key={i} className="px-4 py-2.5 flex items-center justify-between gap-3 hover:bg-vscode-surface transition-colors">
                  <div>
                    <p className="text-sm text-vscode-text capitalize">{run.agent_name.replace(/_/g, ' ')}</p>
                    <p className="text-[11px] text-vscode-muted">{run.started_at ? new Date(run.started_at).toLocaleString() : 'unknown'}</p>
                  </div>
                  <span className={`shrink-0 rounded px-2 py-0.5 text-[11px] font-medium ${runBadge[run.status] ?? 'bg-vscode-surface text-vscode-muted'}`}>
                    {run.status}
                  </span>
                </div>
              ))
            ) : (
              <p className="px-4 py-6 text-xs text-vscode-muted text-center">No agent runs yet — go to Agents to trigger one.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
