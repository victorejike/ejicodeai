'use client';

import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  X,
  Building2,
  MapPin,
  ExternalLink,
  ShieldCheck,
  Sparkles,
  Send,
  Copy,
  Check,
  Users,
  Mail,
  FileText,
  Calendar,
  RefreshCw,
  Briefcase,
  Layers,
  Flame,
} from 'lucide-react';

export interface OpportunityDetailModalProps {
  opportunity: any | null;
  isOpen: boolean;
  onClose: () => void;
  onApplicationDispatched?: (opportunityId: string) => void;
}

export default function OpportunityDetailModal({
  opportunity,
  isOpen,
  onClose,
  onApplicationDispatched,
}: OpportunityDetailModalProps) {
  const [loadingDraft, setLoadingDraft] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [draft, setDraft] = useState<any | null>(null);

  // Form inputs for outreach
  const [subject, setSubject] = useState('');
  const [recipientEmail, setRecipientEmail] = useState('');
  const [recipientName, setRecipientName] = useState('');
  const [coverLetter, setCoverLetter] = useState('');

  // UI state
  const [isSending, setIsSending] = useState(false);
  const [sendSuccess, setSendSuccess] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeOutreachTab, setActiveOutreachTab] = useState<'letter' | 'pitch' | 'followup'>('letter');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!isOpen || !opportunity) {
      setDraft(null);
      setDraftError(null);
      setSendSuccess(false);
      setCopied(false);
      return;
    }

    // Prefill default recipient if scraped contacts are attached
    const contacts = opportunity.contacts || [];
    const bestContact = contacts.find((c: any) => c.email) || contacts[0];
    if (bestContact) {
      setRecipientName(bestContact.name || bestContact.role || '');
      setRecipientEmail(bestContact.email || '');
    } else {
      setRecipientName(opportunity.company_name ? `Hiring Team @ ${opportunity.company_name}` : 'Hiring Team');
      setRecipientEmail('');
    }

    // Automatically generate outreach draft based on candidate ATS profile and opportunity details
    fetchDraft(opportunity.id);
  }, [isOpen, opportunity]);

  const fetchDraft = async (oppId: string) => {
    setLoadingDraft(true);
    setDraftError(null);
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`/api/individual/opportunities/${oppId}/draft-outreach`, {
        method: 'POST',
        headers,
      });

      if (!res.ok) {
        throw new Error('Failed to generate tailored outreach');
      }

      const data = await res.json();
      const draftPack = data.draft || data || {};
      setDraft(draftPack);

      setSubject(
        draftPack.subject ||
        draftPack.subject_line ||
        `Application: ${opportunity.title} — ${draftPack.candidate_name || 'Senior Candidate'}`
      );
      setCoverLetter(
        draftPack.cover_letter ||
        draftPack.cold_pitch ||
        draftPack.cold_outreach_pitch ||
        `Dear ${recipientName || 'Hiring Team'},\n\nI am writing to express my enthusiastic interest in the ${opportunity.title} position at ${opportunity.company_name}...`
      );
      if ((draftPack.contact?.email || draftPack.contact_email) && !recipientEmail) {
        setRecipientEmail(draftPack.contact?.email || draftPack.contact_email);
      }
      if ((draftPack.contact?.name || draftPack.contact_name) && !recipientName) {
        setRecipientName(draftPack.contact?.name || draftPack.contact_name);
      }
    } catch (err: any) {
      console.error(err);
      setDraftError(err.message || 'Could not draft message automatically. You can still write and dispatch outreach.');
      setSubject(`Application: ${opportunity.title}`);
      setCoverLetter(
        `Dear ${recipientName || 'Hiring Team'},\n\nI am applying for the ${opportunity.title} role at ${opportunity.company_name}.\n\nWith extensive experience relevant to your tech stack, I am confident in delivering immediate value to your team.`
      );
    } finally {
      setLoadingDraft(false);
    }
  };

  const handleSendApplication = async () => {
    if (!opportunity) return;
    setIsSending(true);
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch('/api/individual/apply', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          opportunity_id: opportunity.id,
          recipient_email: recipientEmail || undefined,
          recipient_name: recipientName || undefined,
          subject: subject || undefined,
          custom_note: coverLetter,
        }),
      });

      if (res.ok) {
        setSendSuccess(true);
        if (onApplicationDispatched) {
          onApplicationDispatched(opportunity.id);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSending(false);
    }
  };

  const handleCopy = () => {
    const textToCopy = `Subject: ${subject}\n\nTo: ${recipientEmail || 'Hiring Manager'}\n\n${coverLetter}`;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!isOpen || !opportunity || !mounted) return null;

  const contacts = opportunity.contacts || [];

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-6"
      role="dialog"
      aria-modal="true"
    >
      {/* Backdrop */}
      <button
        type="button"
        aria-label="Close"
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-black/75 backdrop-blur-md transition-opacity"
      />

      {/* Modal Window */}
      <div className="relative w-full max-w-5xl rounded-3xl bg-[#0d0d12] border border-white/10 shadow-[0_20px_70px_rgba(0,0,0,0.8)] max-h-[92vh] flex flex-col overflow-hidden text-white">
        {/* Top Header */}
        <div className="p-5 sm:p-6 border-b border-white/[0.08] flex items-start justify-between gap-4 bg-[#111118]/80 backdrop-blur-xl">
          <div className="space-y-1.5 min-w-0">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="px-2.5 py-0.5 text-xs font-mono font-bold rounded-lg bg-red-500/15 text-red-400 border border-red-500/30">
                {opportunity.score || opportunity.match_score || 95}% ATS Fit
              </span>
              <span className="px-2.5 py-0.5 text-xs font-mono font-medium rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>{opportunity.safety_status || 'VERIFIED SAFE'}</span>
              </span>
              <span className="px-2.5 py-0.5 text-xs font-mono rounded-lg bg-white/[0.06] text-zinc-300">
                Source: {opportunity.source_platform || 'Live Web Crawl'}
              </span>
              {opportunity.source_url && (
                <a
                  href={opportunity.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-2.5 py-0.5 text-xs font-mono rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 hover:bg-blue-500/20 transition-colors flex items-center gap-1"
                >
                  <span>Original Job Link</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>

            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white truncate">
              {opportunity.title}
            </h2>

            <div className="flex items-center gap-3 text-xs text-zinc-400 flex-wrap">
              <span className="font-semibold text-zinc-200 flex items-center gap-1">
                <Building2 className="w-3.5 h-3.5 text-red-400" />
                {opportunity.company_name}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-zinc-500" />
                {opportunity.location || opportunity.location_type || 'Remote'}
              </span>
              <span>•</span>
              <span className="font-mono text-emerald-400 font-semibold">
                {opportunity.salary_min && opportunity.salary_max
                  ? `$${(opportunity.salary_min / 1000).toFixed(0)}k - $${(opportunity.salary_max / 1000).toFixed(0)}k`
                  : 'Competitive Market Salary'}
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-zinc-400 hover:text-white hover:bg-white/[0.08] transition-colors shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body: Two Columns */}
        <div className="flex-1 overflow-y-auto grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-white/[0.08]">
          {/* LEFT: Full Job Brief, Requirements & Scraped Contacts (5 cols) */}
          <div className="lg:col-span-5 p-5 sm:p-6 space-y-6 overflow-y-auto bg-[#0d0d12]/60">
            {/* Tech Stack Required */}
            <div>
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-2 mb-2.5">
                <Layers className="w-3.5 h-3.5 text-red-400" />
                <span>Required Tech Stack</span>
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {opportunity.tech_required && opportunity.tech_required.length > 0 ? (
                  opportunity.tech_required.map((tech: string, i: number) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 text-xs font-mono rounded-lg bg-white/[0.05] border border-white/10 text-zinc-200"
                    >
                      {tech}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-zinc-500 italic">No specific stack tags specified</span>
                )}
              </div>
            </div>

            {/* Discovered Hiring Contacts (From Scraped Domain) */}
            <div>
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-2 mb-2.5">
                <Users className="w-3.5 h-3.5 text-emerald-400" />
                <span>Discovered Decision-Maker Contacts</span>
              </h3>

              {contacts.length > 0 ? (
                <div className="space-y-2">
                  {contacts.map((contact: any, i: number) => (
                    <div
                      key={i}
                      onClick={() => {
                        if (contact.email) setRecipientEmail(contact.email);
                        if (contact.name) setRecipientName(contact.name);
                      }}
                      className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:border-emerald-500/40 cursor-pointer transition-all flex items-center justify-between gap-3 text-xs group"
                    >
                      <div>
                        <div className="font-semibold text-white group-hover:text-emerald-300">
                          {contact.name || 'Executive Contact'}
                        </div>
                        <div className="text-[11px] text-zinc-400">{contact.role || contact.title || 'Engineering Leadership'}</div>
                        {contact.email && (
                          <div className="text-[11px] font-mono text-emerald-400 mt-0.5 flex items-center gap-1">
                            <Mail className="w-3 h-3" />
                            <span>{contact.email}</span>
                          </div>
                        )}
                      </div>
                      <span className="text-[10px] font-mono text-zinc-500 bg-white/[0.05] px-2 py-0.5 rounded">
                        {contact.confidence_score ? `${contact.confidence_score}% Conf` : 'Verified'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] text-xs text-zinc-400 flex items-center gap-2">
                  <Mail className="w-4 h-4 text-zinc-500 shrink-0" />
                  <span>
                    Direct leadership email routing through {opportunity.company_domain || 'employer domain'}.
                  </span>
                </div>
              )}
            </div>

            {/* Job Brief & Full Description */}
            <div>
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-2 mb-2.5">
                <Briefcase className="w-3.5 h-3.5 text-blue-400" />
                <span>Job Brief &amp; Posting Details</span>
              </h3>
              <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] text-xs text-zinc-300 leading-relaxed max-h-72 overflow-y-auto whitespace-pre-line font-sans">
                {opportunity.description || opportunity.raw_description || 'Detailed posting information indexed by Job Scout agent.'}
              </div>
            </div>
          </div>

          {/* RIGHT: AI Tailored Outreach & Dispatch (7 cols) */}
          <div className="lg:col-span-7 p-5 sm:p-6 space-y-5 bg-[#101016]/90 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">AI Tailored Outreach Pack</h3>
                    <p className="text-[11px] text-zinc-400">
                      Drafted by Proposal Agent based on your ATS profile &amp; job tech requirements
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 bg-black/40 p-1 rounded-xl border border-white/10 text-xs">
                  <button
                    type="button"
                    onClick={() => setActiveOutreachTab('letter')}
                    className={`px-3 py-1 rounded-lg font-medium transition-all ${
                      activeOutreachTab === 'letter'
                        ? 'bg-red-500/20 text-red-300 font-bold border border-red-500/40'
                        : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    Cover Letter
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveOutreachTab('pitch')}
                    className={`px-3 py-1 rounded-lg font-medium transition-all ${
                      activeOutreachTab === 'pitch'
                        ? 'bg-red-500/20 text-red-300 font-bold border border-red-500/40'
                        : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    Direct Pitch
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveOutreachTab('followup')}
                    className={`px-3 py-1 rounded-lg font-medium transition-all ${
                      activeOutreachTab === 'followup'
                        ? 'bg-red-500/20 text-red-300 font-bold border border-red-500/40'
                        : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    Follow-Up Cadence
                  </button>
                </div>
              </div>

              {loadingDraft ? (
                <div className="p-12 rounded-2xl bg-black/30 border border-white/[0.08] text-center space-y-3">
                  <RefreshCw className="w-6 h-6 animate-spin text-red-400 mx-auto" />
                  <div className="text-xs font-mono text-zinc-300">
                    Synthesizing high-converting tailored outreach using your ATS profile...
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {/* Recipient info */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-mono text-zinc-400 mb-1">
                        RECIPIENT NAME / ROLE
                      </label>
                      <input
                        type="text"
                        value={recipientName}
                        onChange={(e) => setRecipientName(e.target.value)}
                        placeholder="e.g. Alex (Engineering Director)"
                        className="w-full px-3 py-2 rounded-xl bg-black/40 border border-white/10 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-red-500"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-mono text-zinc-400 mb-1">
                        RECIPIENT EMAIL
                      </label>
                      <input
                        type="email"
                        value={recipientEmail}
                        onChange={(e) => setRecipientEmail(e.target.value)}
                        placeholder="e.g. alex@company.com"
                        className="w-full px-3 py-2 rounded-xl bg-black/40 border border-white/10 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-red-500 font-mono"
                      />
                    </div>
                  </div>

                  {/* Subject Line */}
                  <div>
                    <label className="block text-[11px] font-mono text-zinc-400 mb-1">
                      SUBJECT LINE
                    </label>
                    <input
                      type="text"
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      placeholder="Subject Line"
                      className="w-full px-3 py-2 rounded-xl bg-black/40 border border-white/10 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-red-500 font-medium"
                    />
                  </div>

                  {/* Tab View: Letter, Pitch, or Follow-up */}
                  {activeOutreachTab === 'letter' && (
                    <div>
                      <label className="block text-[11px] font-mono text-zinc-400 mb-1">
                        TAILORED APPLICATION COVER LETTER (EDITABLE)
                      </label>
                      <textarea
                        rows={10}
                        value={coverLetter}
                        onChange={(e) => setCoverLetter(e.target.value)}
                        className="w-full p-3.5 rounded-xl bg-black/50 border border-white/10 text-xs text-zinc-200 focus:outline-none focus:border-red-500 font-sans leading-relaxed resize-none"
                      />
                    </div>
                  )}

                  {activeOutreachTab === 'pitch' && (
                    <div className="space-y-2">
                      <label className="block text-[11px] font-mono text-zinc-400">
                        EXECUTIVE DIRECT PITCH (COLD OUTREACH)
                      </label>
                      <div className="p-3.5 rounded-xl bg-black/50 border border-white/10 text-xs text-zinc-200 leading-relaxed font-sans whitespace-pre-line">
                        {draft?.cold_outreach_pitch ||
                          `Hi ${recipientName},\n\nI noticed ${opportunity.company_name} is scaling engineering with ${opportunity.title}. Given my recent track record building high-concurrency systems matching your requirements, I’d love to explore how I can support your roadmap.`}
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          if (draft?.cold_outreach_pitch) {
                            setCoverLetter(draft.cold_outreach_pitch);
                            setActiveOutreachTab('letter');
                          }
                        }}
                        className="text-xs text-red-400 hover:text-red-300 underline font-medium"
                      >
                        Use this pitch as my main outreach message
                      </button>
                    </div>
                  )}

                  {activeOutreachTab === 'followup' && (
                    <div className="space-y-2.5">
                      <label className="block text-[11px] font-mono text-zinc-400">
                        SCHEDULED MULTI-CHANNEL FOLLOW-UP CADENCE
                      </label>
                      <div className="space-y-2 text-xs">
                        <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.08]">
                          <div className="font-bold text-red-400 mb-1">Day 3 Check-in:</div>
                          <div className="text-zinc-300">{draft?.follow_up_cadence?.day_3 || 'Polite follow-up verifying receipt and highlighting key technical alignment.'}</div>
                        </div>
                        <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.08]">
                          <div className="font-bold text-red-400 mb-1">Day 7 Value-Add:</div>
                          <div className="text-zinc-300">{draft?.follow_up_cadence?.day_7 || 'Share relevant architecture insight or relevant portfolio repository sample.'}</div>
                        </div>
                        <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.08]">
                          <div className="font-bold text-red-400 mb-1">Day 14 Final Note:</div>
                          <div className="text-zinc-300">{draft?.follow_up_cadence?.day_14 || 'Graceful close keeping communication lines open for future roadmap needs.'}</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Bottom Actions */}
            <div className="pt-4 border-t border-white/[0.08] flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleCopy}
                  className="px-3.5 py-2 rounded-xl bg-white/[0.05] hover:bg-white/10 text-xs font-medium text-zinc-300 hover:text-white transition-colors flex items-center gap-1.5"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied to Clipboard!' : 'Copy Message'}</span>
                </button>

                <button
                  type="button"
                  onClick={() => fetchDraft(opportunity.id)}
                  disabled={loadingDraft}
                  className="px-3 py-2 rounded-xl text-zinc-400 hover:text-white text-xs flex items-center gap-1 transition-colors"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingDraft ? 'animate-spin' : ''}`} />
                  <span>Regenerate</span>
                </button>
              </div>

              <div className="flex items-center gap-3">
                {sendSuccess ? (
                  <div className="px-4 py-2 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-bold flex items-center gap-2">
                    <Check className="w-4 h-4" />
                    <span>Application Outreach Dispatched!</span>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={handleSendApplication}
                    disabled={isSending || loadingDraft}
                    className="px-6 py-2.5 bg-gradient-to-r from-red-600 to-rose-600 hover:from-rose-600 hover:to-red-600 disabled:opacity-50 text-white text-xs font-bold rounded-xl flex items-center gap-2 shadow-lg shadow-red-600/30 hover:shadow-red-600/50 transition-all transform hover:-translate-y-0.5"
                  >
                    {isSending ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                    <span>{isSending ? 'Dispatching Outreach…' : 'Send Application Outreach'}</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
