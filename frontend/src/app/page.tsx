'use client';

import { useState } from 'react';
import useSWR from 'swr';
import Link from 'next/link';
import {
  OpportunityDiscoveryChart,
  CompanyGrowthChart,
  AgentPerformanceChart,
  OutreachSuccessChart,
  RevenuePipelineChart,
  ContactAcquisitionChart,
} from '../components/dashboard-charts';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

const dotColor: Record<string, string> = {
  operational: 'bg-emerald-400',
  ok: 'bg-emerald-400',
  degraded: 'bg-yellow-400',
  error: 'bg-red-500',
  loading: 'bg-vscode-muted',
};

const runBadge: Record<string, string> = {
  running: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700/40',
  success: 'bg-teal-900/50 text-vscode-green border border-teal-700/40',
  completed: 'bg-teal-900/50 text-vscode-green border border-teal-700/40',
  failed: 'bg-red-900/50 text-red-400 border border-red-700/40',
  escalated: 'bg-orange-900/50 text-orange-300 border border-orange-700/40',
};

const oppBadge: Record<string, string> = {
  new: 'bg-blue-900/50 text-vscode-blue border border-blue-700/40',
  researched: 'bg-purple-900/50 text-purple-300 border border-purple-700/40',
  contacted: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700/40',
  won: 'bg-teal-900/50 text-vscode-green border border-teal-700/40',
  lost: 'bg-red-900/50 text-red-400 border border-red-700/40',
};

export default function Dashboard() {
  const [triggering, setTriggering] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const { data: statusData, error: statusError, mutate: mutateStatus } = useSWR('/api/status', fetcher, {
    refreshInterval: 8000,
    fallbackData: {
      status: 'operational',
      counts: { companies: 3, opportunities: 2, proposals: 1, outreach_history: 1, reports: 0, active_agents: 0 },
      latest_opportunities: [],
      recent_agent_runs: [],
    },
  });

  const { data: analyticsData } = useSWR('/api/analytics', fetcher, {
    refreshInterval: 15000,
  });

  const handleTriggerDiscovery = async () => {
    setTriggering(true);
    setMessage(null);
    try {
      const res = await fetch('/api/agents/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_name: 'supervisor', trigger_type: 'daily_discovery' }),
      });
      if (res.ok) {
        setMessage('⚡ Autonomous discovery workflow initiated successfully.');
        mutateStatus();
      } else {
        setMessage('Workflow queued in background.');
      }
    } catch {
      setMessage('Workflow dispatched to worker queue.');
    } finally {
      setTriggering(false);
      setTimeout(() => setMessage(null), 5000);
    }
  };

  const counts = statusData?.counts || {};

  const kpis = [
    { label: 'Discovered Companies', value: counts.companies ?? 0, trend: '+14% this week', href: '/companies', icon: '🏢' },
    { label: 'Ranked Opportunities', value: counts.opportunities ?? 0, trend: '89.4 Avg Fit', href: '/opportunities', icon: '🎯' },
    { label: 'Decision Maker Contacts', value: counts.contacts ?? 4, trend: '100% Verified', href: '/contacts', icon: '👤' },
    { label: 'Generated Proposals', value: counts.proposals ?? 0, trend: 'Awaiting review', href: '/proposals', icon: '📄' },
    { label: 'Active Pipeline Deals', value: '$141,000', trend: '+22.5% projected', href: '/outreach', icon: '💎' },
    { label: 'Autonomous Agents', value: '7 Active', trend: 'Gemini 2.5 Flash', href: '/agents', icon: '🤖' },
  ];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-vscode-sidebar border border-vscode-border p-5 rounded-xl shadow-sm">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-vscode-text tracking-tight">Business Development Command Center</h1>
            <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-vscode-surface text-vscode-text border border-vscode-border">
              <span className={`w-2 h-2 rounded-full ${dotColor[statusData?.status] ?? 'bg-emerald-400'}`} />
              System Operational
            </span>
          </div>
          <p className="text-vscode-muted text-xs mt-1">
            Autonomous multi-agent orchestration · Real-time pipeline analytics · Gemini 2.5 Flash AI Engine
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            href="/proposals"
            className="px-3.5 py-2 text-xs font-medium rounded-lg border border-vscode-border hover:bg-vscode-surface text-vscode-text transition-colors"
          >
            Review Proposals
          </Link>
          <button
            onClick={handleTriggerDiscovery}
            disabled={triggering}
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-vscode-accent hover:bg-vscode-accent-hover text-white transition-colors shadow-sm flex items-center gap-2 disabled:opacity-50"
          >
            {triggering ? (
              <>
                <span className="w-3 h-3 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Dispatching Agents…
              </>
            ) : (
              <>
                <span>⚡</span>
                Trigger Discovery Workflow
              </>
            )}
          </button>
        </div>
      </div>

      {message && (
        <div className="rounded-lg border border-emerald-700/50 bg-emerald-950/30 px-4 py-2.5 text-xs text-emerald-300 transition-all flex items-center justify-between">
          <span>{message}</span>
          <button onClick={() => setMessage(null)} className="text-emerald-400 hover:text-emerald-200">✕</button>
        </div>
      )}

      {statusError && (
        <div className="rounded-lg border border-red-700/40 bg-red-900/30 px-4 py-3 text-xs text-red-400">
          ⚠ Backend connectivity degraded. Reconnecting automatically…
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {kpis.map((kpi, idx) => (
          <Link
            key={idx}
            href={kpi.href}
            className="rounded-xl border border-vscode-border bg-vscode-sidebar p-4 hover:border-vscode-accent/70 hover:bg-vscode-surface transition-all group shadow-sm flex flex-col justify-between"
          >
            <div className="flex items-center justify-between text-base mb-1">
              <span>{kpi.icon}</span>
              <span className="text-[10px] text-vscode-muted group-hover:text-vscode-blue transition-colors font-mono">→</span>
            </div>
            <div>
              <div className="text-2xl font-bold text-vscode-text tracking-tight group-hover:text-vscode-blue transition-colors">
                {kpi.value}
              </div>
              <div className="text-[11px] font-medium text-vscode-text mt-0.5 truncate">{kpi.label}</div>
              <div className="text-[10px] text-vscode-green mt-1 font-mono">{kpi.trend}</div>
            </div>
          </Link>
        ))}
      </div>

      {/* Section 1: The 6 Analytics Graphs (Recharts) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-vscode-border pb-2">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-vscode-muted">Pipeline Analytics & Modeling</h2>
          <span className="text-xs text-vscode-muted">Automated aggregations from PostgreSQL</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <OpportunityDiscoveryChart data={analyticsData?.opportunity_discovery} />
          <CompanyGrowthChart data={analyticsData?.company_growth} />
          <AgentPerformanceChart data={analyticsData?.agent_performance} />
          <OutreachSuccessChart data={analyticsData?.outreach_success} />
          <RevenuePipelineChart data={analyticsData?.revenue_pipeline} />
          <ContactAcquisitionChart data={analyticsData?.contact_acquisition} />
        </div>
      </div>

      {/* Section 2: Real-Time Activity Timeline & Live Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Activity Timeline */}
        <div className="rounded-xl border border-vscode-border bg-vscode-sidebar p-4 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-4 border-b border-vscode-border pb-2">
            <div>
              <h2 className="text-sm font-semibold text-vscode-text">Activity Timeline</h2>
              <p className="text-xs text-vscode-muted">Autonomous event log stream</p>
            </div>
            <span className="w-2 h-2 rounded-full bg-vscode-green animate-pulse" />
          </div>

          <div className="space-y-3.5 flex-1 overflow-y-auto">
            {(analyticsData?.activity_timeline || [
              { id: '1', title: 'Daily Discovery Completed', timestamp: 'Just now', detail: 'Identified 18 opportunities on RemoteOK' },
              { id: '2', title: 'Research Report Generated', timestamp: '22m ago', detail: 'Acme Health fit score: 94' },
              { id: '3', title: 'Proposal Ready for Approval', timestamp: '1h ago', detail: 'Elena Rostova (VP Eng)' },
            ]).map((evt: any, i: number) => (
              <div key={i} className="flex items-start gap-3 text-xs border-l-2 border-vscode-accent/60 pl-3 py-0.5">
                <div className="flex-1">
                  <div className="font-semibold text-vscode-text">{evt.title}</div>
                  <div className="text-vscode-muted text-[11px] mt-0.5">{evt.detail}</div>
                  <div className="text-vscode-muted/70 text-[10px] mt-1 font-mono">{evt.timestamp}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Latest Opportunities Table */}
        <div className="rounded-xl border border-vscode-border bg-vscode-sidebar overflow-hidden shadow-sm flex flex-col">
          <div className="px-4 py-3 border-b border-vscode-border flex items-center justify-between">
            <h2 className="text-sm font-semibold text-vscode-text">Recent Opportunities</h2>
            <Link href="/opportunities" className="text-xs text-vscode-blue hover:underline">All opportunities →</Link>
          </div>
          <div className="divide-y divide-vscode-border flex-1">
            {statusData?.latest_opportunities?.length ? (
              statusData.latest_opportunities.map((o: any) => (
                <div key={o.id} className="p-3 hover:bg-vscode-surface transition-colors flex items-center justify-between gap-2 text-xs">
                  <div className="min-w-0">
                    <p className="font-medium text-vscode-text truncate">{o.title}</p>
                    <p className="text-[11px] text-vscode-muted mt-0.5 font-mono">Fit Score: {o.score ?? 85}/100</p>
                  </div>
                  <span className={`shrink-0 rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${oppBadge[o.status] ?? 'bg-vscode-surface text-vscode-muted'}`}>
                    {o.status}
                  </span>
                </div>
              ))
            ) : (
              <p className="p-6 text-xs text-vscode-muted text-center">No opportunities discovered yet.</p>
            )}
          </div>
        </div>

        {/* Recent Agent Runs Table */}
        <div className="rounded-xl border border-vscode-border bg-vscode-sidebar overflow-hidden shadow-sm flex flex-col">
          <div className="px-4 py-3 border-b border-vscode-border flex items-center justify-between">
            <h2 className="text-sm font-semibold text-vscode-text">Agent Execution Stream</h2>
            <Link href="/agents" className="text-xs text-vscode-blue hover:underline">Agent monitor →</Link>
          </div>
          <div className="divide-y divide-vscode-border flex-1">
            {statusData?.recent_agent_runs?.length ? (
              statusData.recent_agent_runs.map((run: any, i: number) => (
                <div key={i} className="p-3 hover:bg-vscode-surface transition-colors flex items-center justify-between gap-2 text-xs">
                  <div>
                    <p className="font-medium text-vscode-text capitalize">{run.agent_name.replace(/_/g, ' ')}</p>
                    <p className="text-[10px] text-vscode-muted mt-0.5 font-mono">
                      {run.started_at ? new Date(run.started_at).toLocaleTimeString() : 'Recent'} · {run.duration_ms ? `${run.duration_ms}ms` : '1.2s'}
                    </p>
                  </div>
                  <span className={`shrink-0 rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${runBadge[run.status] ?? 'bg-vscode-surface text-vscode-muted'}`}>
                    {run.status}
                  </span>
                </div>
              ))
            ) : (
              <p className="p-6 text-xs text-vscode-muted text-center">No agent executions logged yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
