'use client';

import useSWR from 'swr';
import { useState } from 'react';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

type AgentStatus = { agent_name: string; status: string; last_run: string | null; last_duration_ms: number | null; last_error: string | null };
type AgentRun = { id: string; agent_name: string; status: string; started_at: string | null; completed_at: string | null; duration_ms: number | null; items_processed: number; items_created: number; error_message: string | null };

const badge: Record<string, string> = {
  never_run: 'bg-vscode-surface text-vscode-muted border border-vscode-border',
  running: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700/40',
  success: 'bg-teal-900/50 text-vscode-green border border-teal-700/40',
  completed: 'bg-teal-900/50 text-vscode-green border border-teal-700/40',
  failure: 'bg-red-900/50 text-red-400 border border-red-700/40',
  failed: 'bg-red-900/50 text-red-400 border border-red-700/40',
  escalated: 'bg-orange-900/50 text-orange-300 border border-orange-700/40',
};

const agentDesc: Record<string, string> = {
  supervisor: 'Orchestrates all agents',
  job_scout: 'Discovers job opportunities',
  company_scout: 'Finds target companies',
  research: 'Deep company analysis',
  ranking: 'Scores & ranks leads',
  contact_discovery: 'Finds decision makers',
  knowledge_base: 'Manages RAG embeddings',
  proposal_generation: 'Generates outreach content',
  outreach: 'Sends approved emails',
  reply_monitoring: 'Monitors email replies',
};

export default function AgentsPage() {
  const { data, error, isLoading, mutate } = useSWR('/api/agents', fetcher, {
    fallbackData: { agents: [], runs: [] },
    refreshInterval: 10000,
  });
  const [triggering, setTriggering] = useState<string | null>(null);
  const [triggered, setTriggered] = useState<string | null>(null);

  const triggerAgent = async (name: string) => {
    setTriggering(name);
    try {
      await fetch(`/api/agents/${name}/trigger`, { method: 'POST' });
      setTriggered(name);
      setTimeout(() => setTriggered(null), 3000);
      await mutate();
    } finally { setTriggering(null); }
  };

  return (
    <div>
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-vscode-text">Agent Monitor</h1>
          <p className="text-vscode-muted text-xs mt-0.5">View status, trigger runs, inspect history · auto-refreshes every 10s</p>
        </div>
        <button onClick={() => mutate()} className="self-start sm:self-auto rounded border border-vscode-border px-3 py-1.5 text-xs text-vscode-muted hover:text-vscode-text hover:bg-vscode-surface transition-colors">
          ↻ Refresh
        </button>
      </div>

      {isLoading && <p className="text-vscode-muted text-xs mb-4 animate-pulse">Loading agent data…</p>}
      {error && <p className="text-red-400 text-xs mb-4">Failed to load agent data.</p>}

      {triggered && (
        <div className="mb-4 rounded border border-teal-700/40 bg-teal-900/30 px-4 py-2.5 text-xs text-vscode-green">
          ✓ {triggered.replace(/_/g, ' ')} triggered successfully.
        </div>
      )}

      {/* Agent cards */}
      <section className="mb-8">
        <h2 className="text-xs uppercase tracking-widest text-vscode-muted font-semibold mb-3">Agent Status</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {data?.agents?.map((agent: AgentStatus) => (
            <div key={agent.agent_name} className="rounded-lg border border-vscode-border bg-vscode-sidebar p-4 flex flex-col gap-2 hover:border-vscode-accent/50 transition-colors">
              <div className="flex items-center justify-between">
                <span className="font-medium text-vscode-text text-sm capitalize">{agent.agent_name.replace(/_/g, ' ')}</span>
                <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${badge[agent.status] ?? 'bg-vscode-surface text-vscode-muted'}`}>
                  {agent.status}
                </span>
              </div>
              <p className="text-[11px] text-vscode-muted">{agentDesc[agent.agent_name] ?? ''}</p>
              <p className="text-[11px] text-vscode-muted">
                {agent.last_run ? new Date(agent.last_run).toLocaleString() : 'Never run'}
                {agent.last_duration_ms ? ` · ${(agent.last_duration_ms / 1000).toFixed(1)}s` : ''}
              </p>
              {agent.last_error && <p className="text-[11px] text-red-400 truncate">{agent.last_error}</p>}
              <button
                onClick={() => triggerAgent(agent.agent_name)}
                disabled={triggering === agent.agent_name}
                className="mt-auto w-full rounded bg-vscode-accent hover:bg-vscode-accent-hover disabled:opacity-50 px-3 py-1.5 text-xs font-medium text-white transition-colors"
              >
                {triggering === agent.agent_name ? 'Triggering…' : '▶ Trigger'}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Recent runs */}
      <section>
        <h2 className="text-xs uppercase tracking-widest text-vscode-muted font-semibold mb-3">Recent Runs</h2>
        <div className="rounded-lg border border-vscode-border bg-vscode-sidebar overflow-hidden">
          {!data?.runs?.length ? (
            <p className="p-6 text-center text-vscode-muted text-xs">No agent runs recorded yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-vscode-border bg-vscode-surface">
                  <tr>
                    {['Agent', 'Status', 'Started', 'Duration', 'Processed', 'Created'].map(h => (
                      <th key={h} className="px-4 py-2.5 text-left text-[11px] font-semibold text-vscode-muted uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-vscode-border">
                  {data.runs.map((run: AgentRun) => (
                    <tr key={run.id} className="hover:bg-vscode-surface transition-colors">
                      <td className="px-4 py-2.5 text-vscode-text capitalize">{run.agent_name.replace(/_/g, ' ')}</td>
                      <td className="px-4 py-2.5">
                        <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${badge[run.status] ?? 'bg-vscode-surface text-vscode-muted'}`}>{run.status}</span>
                      </td>
                      <td className="px-4 py-2.5 text-vscode-muted text-xs">{run.started_at ? new Date(run.started_at).toLocaleString() : '—'}</td>
                      <td className="px-4 py-2.5 text-vscode-muted text-xs">{run.duration_ms ? `${(run.duration_ms / 1000).toFixed(1)}s` : '—'}</td>
                      <td className="px-4 py-2.5 text-vscode-text">{run.items_processed}</td>
                      <td className="px-4 py-2.5 text-vscode-text">{run.items_created}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
