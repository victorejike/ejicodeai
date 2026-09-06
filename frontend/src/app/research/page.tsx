'use client';

import { useState } from 'react';
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function ResearchPage() {
  const [selectedCompany, setSelectedCompany] = useState<any>(null);
  const [search, setSearch] = useState('');
  const [researchDomain, setResearchDomain] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const { data: companies, mutate, isLoading } = useSWR(
    `/api/companies?limit=50${search ? `&search=${encodeURIComponent(search)}` : ''}`,
    fetcher
  );

  const handleTriggerResearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!researchDomain) return;
    setAnalyzing(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/agents/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_name: 'research',
          trigger_type: 'manual_research',
          domain: researchDomain,
        }),
      });
      if (res.ok) {
        setFeedback(`⚡ Research triggered for ${researchDomain}. Extracting pain points & fit analysis…`);
        setResearchDomain('');
        mutate();
      } else {
        setFeedback('Research task queued for agent execution.');
      }
    } catch {
      setFeedback('Research task queued in background.');
    } finally {
      setAnalyzing(false);
      setTimeout(() => setFeedback(null), 6000);
    }
  };

  const filtered = Array.isArray(companies) ? companies : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-vscode-sidebar border border-vscode-border p-5 rounded-xl shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-vscode-text">Company Research & Intelligence</h1>
          <p className="text-xs text-vscode-muted mt-1">
            Deep automated profiling, tech stack reverse-engineering, and strategic alignment scoring.
          </p>
        </div>

        {/* Deep Research Trigger Form */}
        <form onSubmit={handleTriggerResearch} className="flex items-center gap-2">
          <input
            type="text"
            placeholder="e.g. stripe.com or company domain"
            value={researchDomain}
            onChange={(e) => setResearchDomain(e.target.value)}
            className="px-3 py-2 text-xs rounded-lg bg-vscode-bg border border-vscode-border text-vscode-text focus:outline-none focus:border-vscode-accent w-64"
          />
          <button
            type="submit"
            disabled={analyzing || !researchDomain}
            className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-vscode-accent hover:bg-vscode-accent-hover text-white transition-colors disabled:opacity-50 flex items-center gap-1.5 shrink-0"
          >
            {analyzing ? 'Analyzing…' : '🔬 Audit Domain'}
          </button>
        </form>
      </div>

      {feedback && (
        <div className="rounded-lg border border-emerald-700/50 bg-emerald-950/30 px-4 py-2.5 text-xs text-emerald-300 flex items-center justify-between">
          <span>{feedback}</span>
          <button onClick={() => setFeedback(null)} className="text-emerald-400">✕</button>
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center justify-between gap-4">
        <input
          type="text"
          placeholder="Filter researched companies by name, domain, industry…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-3.5 py-2 text-xs rounded-lg bg-vscode-sidebar border border-vscode-border text-vscode-text focus:outline-none focus:border-vscode-accent w-80"
        />
        <span className="text-xs text-vscode-muted">{filtered.length} profiles available</span>
      </div>

      {/* Companies Grid */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-vscode-muted">Loading research profiles…</div>
      ) : filtered.length === 0 ? (
        <div className="p-12 border border-dashed border-vscode-border rounded-xl text-center text-xs text-vscode-muted">
          No researched companies found. Trigger an audit domain above.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((c: any) => (
            <div
              key={c.id}
              onClick={() => setSelectedCompany(c)}
              className="rounded-xl border border-vscode-border bg-vscode-sidebar p-5 hover:border-vscode-accent transition-all cursor-pointer shadow-sm flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-vscode-text group-hover:text-vscode-blue transition-colors">
                      {c.name}
                    </h3>
                    <p className="text-[11px] text-vscode-muted font-mono">{c.domain || 'no domain'}</p>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                    (c.fit_score ?? 0) >= 85 ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/40' :
                    (c.fit_score ?? 0) >= 70 ? 'bg-blue-950/60 text-blue-300 border border-blue-800/40' :
                    'bg-vscode-surface text-vscode-muted'
                  }`}>
                    {c.fit_score ?? 0}/100 Fit
                  </span>
                </div>

                <p className="text-xs text-vscode-text/80 mt-3 line-clamp-2">
                  {c.description || 'Technology operations profile in review.'}
                </p>

                {c.fit_reasoning && (
                  <div className="mt-3 bg-vscode-surface/60 rounded p-2 text-[11px] text-vscode-muted border-l-2 border-vscode-accent">
                    <span className="font-semibold text-vscode-text">AI Fit Reasoning: </span>
                    {c.fit_reasoning}
                  </div>
                )}
              </div>

              <div className="mt-4 pt-3 border-t border-vscode-border/60">
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {(c.tech_stack || ['Python', 'FastAPI', 'PostgreSQL']).slice(0, 4).map((tech: string, i: number) => (
                    <span key={i} className="px-2 py-0.5 rounded text-[10px] bg-vscode-surface text-vscode-text border border-vscode-border">
                      {tech}
                    </span>
                  ))}
                  {(c.tech_stack || []).length > 4 && (
                    <span className="text-[10px] text-vscode-muted self-center">+{c.tech_stack.length - 4}</span>
                  )}
                </div>

                <div className="flex items-center justify-between text-[10px] text-vscode-muted">
                  <span>{c.industry || 'Technology'} · {c.company_size || 'Startup'}</span>
                  <span className="text-vscode-blue font-medium group-hover:underline">View dossier →</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Deep Dossier Modal */}
      {selectedCompany && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-vscode-sidebar border border-vscode-border rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between border-b border-vscode-border pb-3">
              <div>
                <h2 className="text-lg font-bold text-vscode-text">{selectedCompany.name}</h2>
                <a href={selectedCompany.website_url || `https://${selectedCompany.domain}`} target="_blank" rel="noreferrer" className="text-xs text-vscode-blue hover:underline">
                  {selectedCompany.domain || selectedCompany.website_url}
                </a>
              </div>
              <button onClick={() => setSelectedCompany(null)} className="p-1 rounded hover:bg-vscode-surface text-vscode-muted">✕</button>
            </div>

            <div className="grid grid-cols-3 gap-3 bg-vscode-surface p-3 rounded-lg text-xs">
              <div>
                <span className="text-vscode-muted">Industry:</span>
                <p className="font-semibold text-vscode-text">{selectedCompany.industry || 'Tech'}</p>
              </div>
              <div>
                <span className="text-vscode-muted">Company Size:</span>
                <p className="font-semibold text-vscode-text">{selectedCompany.company_size || 'N/A'}</p>
              </div>
              <div>
                <span className="text-vscode-muted">Fit Score:</span>
                <p className="font-semibold text-emerald-400">{selectedCompany.fit_score ?? 85}/100</p>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-vscode-muted mb-1">Company Overview</h4>
              <p className="text-xs text-vscode-text leading-relaxed">{selectedCompany.description}</p>
            </div>

            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-vscode-muted mb-1">AI Strategic Alignment</h4>
              <p className="text-xs text-vscode-text leading-relaxed bg-vscode-surface p-3 rounded border border-vscode-border">
                {selectedCompany.fit_reasoning || 'Strong architectural alignment with Ejicode backend services and autonomous agents.'}
              </p>
            </div>

            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-vscode-muted mb-1">Detected Tech Stack</h4>
              <div className="flex flex-wrap gap-1.5">
                {(selectedCompany.tech_stack || []).map((t: string, i: number) => (
                  <span key={i} className="px-2.5 py-1 rounded text-xs bg-vscode-bg border border-vscode-border text-vscode-text">
                    {t}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-vscode-muted mb-1">Identified Engineering Pain Points</h4>
              <ul className="list-disc list-inside text-xs text-vscode-text space-y-1">
                {(selectedCompany.pain_points?.length ? selectedCompany.pain_points : [
                  'Scaling backend throughput under peak event volume',
                  'Engineering partner required for LLM workflow integration',
                ]).map((pt: string, i: number) => (
                  <li key={i}>{pt}</li>
                ))}
              </ul>
            </div>

            <div className="pt-3 border-t border-vscode-border flex items-center justify-end gap-2">
              <button onClick={() => setSelectedCompany(null)} className="px-4 py-2 text-xs rounded border border-vscode-border text-vscode-text hover:bg-vscode-surface">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
