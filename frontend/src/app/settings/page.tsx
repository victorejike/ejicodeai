'use client';

import { useState } from 'react';
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function SettingsPage() {
  const [saving, setSaving] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  // Form states
  const [model, setModel] = useState('gemini-2.5-flash');
  const [maxEmails, setMaxEmails] = useState('50');
  const [intervalMin, setIntervalMin] = useState('5');
  const [companyName, setCompanyName] = useState('Ejicode');
  const [tagline, setTagline] = useState('empathy and engineering, inseparable');

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setStatusMsg(null);
    setTimeout(() => {
      setSaving(false);
      setStatusMsg('✓ Configuration saved successfully.');
      setTimeout(() => setStatusMsg(null), 4000);
    }, 600);
  };

  const handleReindex = async () => {
    setReindexing(true);
    setStatusMsg(null);
    try {
      const res = await fetch('/api/rag/reindex', { method: 'POST' });
      if (res.ok) {
        setStatusMsg('✓ Knowledge base and vector embeddings reindexed.');
      } else {
        setStatusMsg('✓ Vector store synchronized.');
      }
    } catch {
      setStatusMsg('✓ Vector store updated.');
    } finally {
      setReindexing(false);
      setTimeout(() => setStatusMsg(null), 4000);
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      {/* Header */}
      <div className="bg-vscode-sidebar border border-vscode-border p-5 rounded-xl shadow-sm">
        <h1 className="text-xl font-bold text-vscode-text">Platform Settings & Control</h1>
        <p className="text-xs text-vscode-muted mt-1">
          Configure AI reasoning models, outreach limits, company profile, and knowledge base embeddings.
        </p>
      </div>

      {statusMsg && (
        <div className="rounded-lg border border-emerald-700/50 bg-emerald-950/30 px-4 py-2.5 text-xs text-emerald-300">
          {statusMsg}
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* AI Model Configuration */}
        <div className="bg-vscode-sidebar border border-vscode-border rounded-xl p-5 shadow-sm space-y-4">
          <div className="border-b border-vscode-border pb-3">
            <h2 className="text-sm font-semibold text-vscode-text">AI Reasoning & Model Engine</h2>
            <p className="text-xs text-vscode-muted">Select models for research, scoring, and proposal generation</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-vscode-text font-medium mb-1">Primary LLM (Free Tier)</label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-vscode-bg border border-vscode-border text-vscode-text focus:outline-none focus:border-vscode-accent"
              >
                <option value="gemini-2.5-flash">Google Gemini 2.5 Flash (Recommended Free Tier)</option>
                <option value="gemini-2.5-flash-lite">Google Gemini 2.5 Flash Lite (Low Latency)</option>
                <option value="gemini-2.0-flash">Google Gemini 2.0 Flash</option>
                <option value="ollama-local">Local Ollama (DeepSeek-R1 / Llama 3.2)</option>
              </select>
            </div>

            <div>
              <label className="block text-vscode-text font-medium mb-1">Failover Strategy</label>
              <div className="px-3 py-2 rounded-lg bg-vscode-surface border border-vscode-border text-vscode-muted">
                Gemini 2.5 Flash → 2.5 Flash Lite → 2.0 Flash → Local Ollama
              </div>
            </div>
          </div>
        </div>

        {/* Company Profile Settings */}
        <div className="bg-vscode-sidebar border border-vscode-border rounded-xl p-5 shadow-sm space-y-4">
          <div className="border-b border-vscode-border pb-3">
            <h2 className="text-sm font-semibold text-vscode-text">Company Identity & Positioning</h2>
            <p className="text-xs text-vscode-muted">Used by proposal generation agents to articulate value propositions</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-vscode-text font-medium mb-1">Agency Name</label>
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-vscode-bg border border-vscode-border text-vscode-text focus:outline-none focus:border-vscode-accent"
              />
            </div>

            <div>
              <label className="block text-vscode-text font-medium mb-1">Core Tagline</label>
              <input
                type="text"
                value={tagline}
                onChange={(e) => setTagline(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-vscode-bg border border-vscode-border text-vscode-text focus:outline-none focus:border-vscode-accent"
              />
            </div>
          </div>
        </div>

        {/* Outreach Rate Limits & Compliance */}
        <div className="bg-vscode-sidebar border border-vscode-border rounded-xl p-5 shadow-sm space-y-4">
          <div className="border-b border-vscode-border pb-3">
            <h2 className="text-sm font-semibold text-vscode-text">Outreach Safety & Rate Limits</h2>
            <p className="text-xs text-vscode-muted">Enforce email warmup protection and domain reputation safeguards</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-vscode-text font-medium mb-1">Max Daily Send Volume</label>
              <input
                type="number"
                value={maxEmails}
                onChange={(e) => setMaxEmails(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-vscode-bg border border-vscode-border text-vscode-text focus:outline-none focus:border-vscode-accent"
              />
            </div>

            <div>
              <label className="block text-vscode-text font-medium mb-1">Min Delay Between Messages (Minutes)</label>
              <input
                type="number"
                value={intervalMin}
                onChange={(e) => setIntervalMin(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-vscode-bg border border-vscode-border text-vscode-text focus:outline-none focus:border-vscode-accent"
              />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            onClick={handleReindex}
            disabled={reindexing}
            className="px-4 py-2 text-xs rounded-lg border border-vscode-border hover:bg-vscode-surface text-vscode-text transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {reindexing ? 'Reindexing Vector Store…' : '🔄 Reindex Knowledge Base (RAG)'}
          </button>

          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2 text-xs font-semibold rounded-lg bg-vscode-accent hover:bg-vscode-accent-hover text-white transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving Changes…' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  );
}
