'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Building2,
  CheckCircle2,
  Mail,
  Phone,
  ShieldCheck,
  User,
  ExternalLink,
  Briefcase,
  Layers,
  AlertCircle,
} from 'lucide-react';

interface ContactDetail {
  id: string;
  email: string;
  full_name?: string | null;
  title?: string | null;
  company_id?: string | null;
  company_name?: string | null;
  phone?: string | null;
  linkedin_url?: string | null;
  is_decision_maker?: boolean;
  email_confidence?: string;
  status?: string;
  metadata?: Record<string, any>;
  created_at?: string;
}

export default function ContactDetailPage({ params }: { params: { contactId: string } }) {
  const { contactId } = params;
  const router = useRouter();
  const [contact, setContact] = useState<ContactDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchContact = async () => {
      try {
        const response = await fetch(`/api/contacts/${contactId}`);
        if (!response.ok) {
          setError('Unable to load contact details or contact not found.');
          setLoading(false);
          return;
        }
        const data = await response.json();
        setContact(data.contact || data);
      } catch (err: any) {
        setError('Network error while retrieving contact details.');
      } finally {
        setLoading(false);
      }
    };
    fetchContact();
  }, [contactId]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="apple-glass rounded-3xl p-8 flex items-center justify-center min-h-[300px]">
          <div className="flex items-center gap-3 text-sm text-[var(--text-muted)]">
            <span className="w-3 h-3 rounded-full bg-red-500 animate-ping" />
            <span>Loading verified contact intelligence…</span>
          </div>
        </div>
      </div>
    );
  }

  if (error || !contact) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="apple-glass rounded-3xl p-8 text-center space-y-4">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto" />
          <h2 className="text-lg font-bold text-white">Contact Unavailable</h2>
          <p className="text-xs text-[var(--text-muted)] max-w-md mx-auto">{error || 'Could not find this contact record.'}</p>
          <Link
            href="/contacts"
            className="apple-button-secondary inline-flex items-center gap-2 px-5 py-2 text-xs font-semibold"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Contacts</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link
            href="/contacts"
            className="inline-flex items-center gap-2 text-xs text-[var(--text-muted)] hover:text-white transition-colors mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Decision Makers</span>
          </Link>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <span>{contact.full_name || contact.email}</span>
            {contact.is_decision_maker && (
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-red-500/20 text-red-400 border border-red-500/30">
                Decision Maker
              </span>
            )}
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            {contact.title || 'Verified Industry Professional'} &bull; Discovered via Autonomous Agent Network
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/contacts"
            className="apple-button-secondary px-4 py-2 text-xs font-semibold flex items-center gap-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>All Contacts</span>
          </Link>
          {contact.email && (
            <a
              href={`mailto:${contact.email}`}
              className="apple-button-primary px-4 py-2 text-xs font-semibold flex items-center gap-2"
            >
              <Mail className="w-3.5 h-3.5" />
              <span>Reach Out</span>
            </a>
          )}
        </div>
      </div>

      {/* Main Intelligence Bento Card */}
      <div className="apple-glass rounded-3xl p-6 sm:p-8 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Email */}
          <div className="apple-glass-subtle rounded-2xl p-4 flex items-start gap-3.5">
            <div className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-400/20 flex items-center justify-center shrink-0 text-blue-400">
              <Mail className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-muted)]">Verified Email</div>
              <div className="text-sm font-semibold text-white truncate mt-0.5 select-all">{contact.email}</div>
              {contact.email_confidence && (
                <div className="text-[10px] font-mono text-emerald-400 mt-1 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Confidence: {contact.email_confidence}</span>
                </div>
              )}
            </div>
          </div>

          {/* Title / Role */}
          <div className="apple-glass-subtle rounded-2xl p-4 flex items-start gap-3.5">
            <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-400/20 flex items-center justify-center shrink-0 text-purple-400">
              <Briefcase className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-muted)]">Position / Title</div>
              <div className="text-sm font-semibold text-white truncate mt-0.5">{contact.title || 'Unknown Role'}</div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">Direct corporate executive capacity</div>
            </div>
          </div>

          {/* Company */}
          <div className="apple-glass-subtle rounded-2xl p-4 flex items-start gap-3.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-400/20 flex items-center justify-center shrink-0 text-emerald-400">
              <Building2 className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-muted)]">Affiliated Company</div>
              <div className="text-sm font-semibold text-white truncate mt-0.5">
                {contact.company_name || contact.company_id || 'Global Enterprise'}
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">Cross-referenced target entity</div>
            </div>
          </div>

          {/* Status & Pipeline */}
          <div className="apple-glass-subtle rounded-2xl p-4 flex items-start gap-3.5">
            <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-400/20 flex items-center justify-center shrink-0 text-amber-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-muted)]">Outreach Status</div>
              <div className="text-sm font-semibold text-white capitalize mt-0.5">{contact.status || 'Active / Discoverable'}</div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">Monitored for replies and engagement</div>
            </div>
          </div>
        </div>

        {/* Action Panel */}
        <div className="pt-4 border-t border-white/10 flex flex-wrap items-center justify-between gap-4">
          <div className="text-xs text-[var(--text-muted)] font-mono">
            Record ID: <span className="text-white font-mono">{contact.id}</span>
          </div>

          <div className="flex items-center gap-3">
            {contact.linkedin_url && (
              <a
                href={contact.linkedin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="apple-button-secondary px-4 py-2 text-xs font-semibold flex items-center gap-1.5"
              >
                <span>LinkedIn Profile</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
            <Link
              href="/proposals"
              className="apple-button-primary px-4 py-2 text-xs font-semibold flex items-center gap-1.5"
            >
              <span>Draft Pitch Proposal</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
