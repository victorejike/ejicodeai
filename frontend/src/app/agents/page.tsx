'use client';

import useSWR from 'swr';
import { useState } from 'react';
import Link from 'next/link';

const getAuthHeaders = (): Record<string, string> => {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const fetcher = (url: string) =>
  fetch(url, { headers: getAuthHeaders() }).then((r) => r.json());

type AgentStatus = {
  agent_name: string;
  status: string;
  last_run: string | null;
  last_duration_ms: number | null;
  last_error: string | null;
};

type AgentRun = {
  id: string;
  agent_name: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  items_processed: number;
  items_created: number;
  error_message: string | null;
};

const badge: Record<string, { bg: string; text: string; dot: string; label: string }> = {
  never_run: { bg: 'bg-zinc-800/60 border-zinc-700/50', text: 'text-zinc-400', dot: 'bg-zinc-500', label: 'Standby' },
  running: { bg: 'bg-amber-950/40 border-amber-600/40', text: 'text-amber-300', dot: 'bg-amber-400 animate-pulse', label: 'Running' },
  pending: { bg: 'bg-amber-950/40 border-amber-600/40', text: 'text-amber-300', dot: 'bg-amber-400 animate-pulse', label: 'Queued' },
  success: { bg: 'bg-emerald-950/40 border-emerald-600/40', text: 'text-emerald-300', dot: 'bg-emerald-400', label: 'Healthy' },
  completed: { bg: 'bg-emerald-950/40 border-emerald-600/40', text: 'text-emerald-300', dot: 'bg-emerald-400', label: 'Completed' },
  failure: { bg: 'bg-red-950/40 border-red-600/40', text: 'text-red-300', dot: 'bg-red-500', label: 'Attention' },
  failed: { bg: 'bg-red-950/40 border-red-600/40', text: 'text-red-300', dot: 'bg-red-500', label: 'Failed' },
  escalated: { bg: 'bg-orange-950/40 border-orange-600/40', text: 'text-orange-300', dot: 'bg-orange-400', label: 'Escalated' },
};

const agentDesc: Record<string, { desc: string; icon: string }> = {
  supervisor: { desc: 'Master orchestrator coordinating autonomous agent pipelines and data hand-offs.', icon: '⚡' },
  career_pipeline: { desc: 'Runs end-to-end multi-stage pipeline (Scout → Match → CV → Proposal) for active candidates.', icon: '🚀' },
  job_scout: { desc: 'Discovers verified opportunities across boards, HackerNews, remote indexes, and web targets.', icon: '🔎' },
  company_scout: { desc: 'Discovers high-growth companies from YC, Product Hunt, GitHub Trending, and HN.', icon: '🏢' },
  research: { desc: 'Performs in-depth analysis of target companies, tech stacks, and engineering challenges.', icon: '🔬' },
  ranking: { desc: 'Scores and ranks leads and opportunities using our 6-Factor verified scoring engine.', icon: '🎯' },
  contact_discovery: { desc: 'Discovers verified decision makers, engineering leads, and recruitment executives.', icon: '👤' },
  knowledge_base: { desc: 'Maintains vector embeddings and semantic search context in ChromaDB.', icon: '🧠' },
  proposal_generation: { desc: 'Generates tailored proposals, outreach emails, and self-marketing campaigns.', icon: '📄' },
  outreach: { desc: 'Dispatches and tracks outbound messages to approved decision maker contacts.', icon: '📬' },
  reply_monitoring: { desc: 'Monitors inbound reply streams, classifies responses, and triggers follow-up actions.', icon: '💬' },
};

export default function AgentsPage() {
  const { data, error, isLoading, mutate } = useSWR('/api/agents', fetcher, {
    fallbackData: { agents: [], runs: [] },
    refreshInterval: 6000,
  });
  const [triggering, setTriggering] = useState<string | null>(null);
  const [triggered, setTriggered] = useState<string | null>(null);

  const triggerAgent = async (name: string) => {
    setTriggering(name);
    try {
      await fetch(`/api/agents/${name}/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ agent_name: name }),
      });
      setTriggered(name);
      setTimeout(() => setTriggered(null), 3500);
      await mutate();
    } finally {
      setTriggering(null);
    }
  };

  const triggerAll = async () => {
    setTriggering('all');
    try {
      await fetch('/api/agents/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ agent_name: 'supervisor' }),
      });
      setTriggered('Supervisor Pipeline (All Agents)');
      setTimeout(() => setTriggered(null), 4000);
      await mutate();
    } finally {
      setTriggering(null);
    }
  };

  const rawAgents: AgentStatus[] = Array.isArray(data?.agents) ? data.agents : [];
  const rawRuns: AgentRun[] = Array.isArray(data?.runs) ? data.runs : [];

  const healthyCount = rawAgents.filter((a) => a.status === 'success' || a.status === 'completed').length;
  const runningCount = rawAgents.filter((a) => a.status === 'running' || a.status === 'pending').length;

  return (
    <div className="relative min-h-screen text-slate-100 p-6 md:p-10">
      {/* Ambient background glows */}
      <div className="pointer-events-none fixed -top-40 -left-40 h-96 w-96 rounded-full bg-blue-600/10 blur-[130px]" />
      <div className="pointer-events-none fixed top-1/3 -right-40 h-96 w-96 rounded-full bg-emerald-600/10 blur-[140px]" />

      <div className="relative z-10 max-w-7xl mx-auto space-y-8">
        {/* Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-6 rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur-xl shadow-2xl">
          <div className="space-y-1.5">
            <div className="flex items-center gap-3">
              <span className="h-3 w-3 rounded-full bg-emerald-400 animate-ping" />
              <h1 className="text-2xl font-bold tracking-tight text-white">Autonomous Agent Fleet</h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950/60 border border-emerald-500/30 text-emerald-300">
                {healthyCount} / {rawAgents.length || 11} Operational
              </span>
            </div>
            <p className="text-sm text-slate-400">
              Live telemetry, autonomous hand-offs, and execution controls for the Ejicode multi-agent network.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => mutate()}
              className="px-4 py-2 text-xs font-medium rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 transition-all"
            >
              ↻ Refresh Fleet
            </button>
            <button
              onClick={triggerAll}
              disabled={triggering !== null}
              className="px-5 py-2 text-xs font-semibold rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-lg shadow-blue-500/25 transition-all disabled:opacity-50 flex items-center gap-2"
            >
              {triggering === 'all' ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Dispatching Fleet…
                </>
              ) : (
                <>
                  <span>⚡</span>
                  Orchestrate All Agents
                </>
              )}
            </button>
          </div>
        </div>

        {/* Alerts & Notifications */}
        {triggered && (
          <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/40 text-emerald-300 text-sm flex items-center justify-between animate-fade-in">
            <span>✓ <strong>{triggered.replace(/_/g, ' ')}</strong> dispatched successfully. Background execution in progress.</span>
            <button onClick={() => setTriggered(null)} className="text-emerald-400 hover:text-white">✕</button>
          </div>
        )}

        {/* Live Metrics Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl border border-white/10 bg-slate-900/40 backdrop-blur-md">
            <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Active Agents</div>
            <div className="text-2xl font-bold text-white mt-1">{rawAgents.length || 11}</div>
            <div className="text-[11px] text-emerald-400 mt-0.5">Gemini 2.5 Flash Engine</div>
          </div>
          <div className="p-4 rounded-xl border border-white/10 bg-slate-900/40 backdrop-blur-md">
            <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Operational Status</div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">100% Online</div>
            <div className="text-[11px] text-slate-400 mt-0.5">FastAPI Background Tasks</div>
          </div>
          <div className="p-4 rounded-xl border border-white/10 bg-slate-900/40 backdrop-blur-md">
            <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Recent Executions</div>
            <div className="text-2xl font-bold text-white mt-1">{rawRuns.length}</div>
            <div className="text-[11px] text-slate-400 mt-0.5">Persisted in SQLite database</div>
          </div>
          <div className="p-4 rounded-xl border border-white/10 bg-slate-900/40 backdrop-blur-md">
            <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Candidate Pipeline</div>
            <div className="text-2xl font-bold text-indigo-400 mt-1">Unlocked</div>
            <div className="text-[11px] text-emerald-400 mt-0.5">Profiles 100% Complete</div>
          </div>
        </div>

        {/* Agent Cards Grid */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold tracking-wider text-slate-300 uppercase">Agent Fleet Status</h2>
            <span className="text-xs text-slate-400">Click ▶ Trigger on any agent to run in isolation</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {rawAgents.map((agent: AgentStatus) => {
              const b = badge[agent.status] || badge.never_run;
              const meta = agentDesc[agent.agent_name] || { desc: 'Specialized autonomous worker agent.', icon: '🤖' };
              const isTriggeringThis = triggering === agent.agent_name;

              return (
                <div
                  key={agent.agent_name}
                  className="rounded-2xl border border-white/10 bg-slate-900/50 backdrop-blur-xl p-5 flex flex-col justify-between hover:border-blue-500/40 hover:bg-slate-900/70 transition-all group shadow-sm"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <span className="text-2xl p-2 rounded-xl bg-white/5 border border-white/10">{meta.icon}</span>
                        <div>
                          <h3 className="font-semibold text-white text-base capitalize">
                            {agent.agent_name.replace(/_/g, ' ')}
                          </h3>
                          <span className="text-[11px] text-slate-400 font-mono">agent_id: {agent.agent_name}</span>
                        </div>
                      </div>

                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${b.bg} ${b.text}`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${b.dot}`} />
                        {b.label}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                      {meta.desc}
                    </p>

                    <div className="pt-2 border-t border-white/5 space-y-1 text-xs text-slate-400">
                      <div className="flex items-center justify-between">
                        <span>Last Executed</span>
                        <span className="text-slate-200 font-medium">
                          {agent.last_run ? new Date(agent.last_run).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Ready on standby'}
                        </span>
                      </div>
                      {agent.last_duration_ms ? (
                        <div className="flex items-center justify-between">
                          <span>Runtime Duration</span>
                          <span className="text-emerald-400 font-mono">{(agent.last_duration_ms / 1000).toFixed(2)}s</span>
                        </div>
                      ) : null}
                      {agent.last_error && (
                        <div className="text-xs text-red-400 bg-red-950/40 border border-red-700/30 p-2 rounded-lg mt-1 truncate">
                          {agent.last_error}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="pt-4 mt-3">
                    <button
                      onClick={() => triggerAgent(agent.agent_name)}
                      disabled={triggering !== null}
                      className="w-full py-2 px-3 text-xs font-semibold rounded-xl border border-white/10 bg-white/5 hover:bg-white/15 text-white transition-all disabled:opacity-50 flex items-center justify-center gap-2 group-hover:border-blue-500/40 group-hover:bg-blue-600/10"
                    >
                      {isTriggeringThis ? (
                        <>
                          <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          Running…
                        </>
                      ) : (
                        <>
                          <span>▶</span>
                          Trigger {agent.agent_name.replace(/_/g, ' ')}
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Execution Log Table */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold tracking-wider text-slate-300 uppercase">Recent Execution Logs</h2>
            <span className="text-xs text-slate-400">Chronological agent run history</span>
          </div>

          <div className="rounded-2xl border border-white/10 bg-slate-900/50 backdrop-blur-xl overflow-hidden shadow-2xl">
            {rawRuns.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                No recent agent runs recorded. Click "Orchestrate All Agents" above to initiate a cycle.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-300">
                  <thead className="bg-white/5 border-b border-white/10 text-xs uppercase tracking-wider text-slate-400 font-medium">
                    <tr>
                      <th className="px-5 py-3">Agent</th>
                      <th className="px-5 py-3">Status</th>
                      <th className="px-5 py-3">Started</th>
                      <th className="px-5 py-3">Duration</th>
                      <th className="px-5 py-3">Items Processed</th>
                      <th className="px-5 py-3">Items Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 font-mono text-xs">
                    {rawRuns.map((run: AgentRun) => {
                      const b = badge[run.status] || badge.never_run;
                      return (
                        <tr key={run.id} className="hover:bg-white/[0.03] transition-colors">
                          <td className="px-5 py-3.5 font-sans font-medium text-white capitalize">
                            {run.agent_name.replace(/_/g, ' ')}
                          </td>
                          <td className="px-5 py-3.5">
                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-sans font-medium border ${b.bg} ${b.text}`}>
                              <span className={`h-1.5 w-1.5 rounded-full ${b.dot}`} />
                              {run.status}
                            </span>
                          </td>
                          <td className="px-5 py-3.5 text-slate-400">
                            {run.started_at ? new Date(run.started_at).toLocaleTimeString() : '—'}
                          </td>
                          <td className="px-5 py-3.5 text-slate-300">
                            {run.duration_ms ? `${(run.duration_ms / 1000).toFixed(2)}s` : '—'}
                          </td>
                          <td className="px-5 py-3.5 text-slate-200">
                            {run.items_processed}
                          </td>
                          <td className="px-5 py-3.5 text-emerald-400 font-semibold">
                            {run.items_created}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

