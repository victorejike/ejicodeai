'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ArrowRight,
  Bot,
  Briefcase,
  Building2,
  Check,
  CheckCircle2,
  Eye,
  FileText,
  Handshake,
  KeyRound,
  Layers,
  ListChecks,
  Radar,
  ScanSearch,
  Search,
  Send,
  ShieldCheck,
  Target,
  TrendingUp,
  UserCheck,
  Users,
} from 'lucide-react';
import { useSession } from '@/lib/useSession';

interface PublicMetrics {
  total_opportunities_indexed: number;
  total_companies_verified: number;
  contacts_discovered: number;
  outreach_delivered: number;
  candidates_matched: number;
  rejection_recovery_rate: number | null;
  data_extraction_accuracy: number | null;
  active_sources_count: number;
  workflow_stages_count: number;
}

const INDIVIDUAL_STEPS = [
  {
    icon: FileText,
    title: 'Upload your CV',
    desc: 'The AI reads your CV, portfolio, and public profiles and extracts real skills, experience, and education — nothing invented.',
  },
  {
    icon: ScanSearch,
    title: 'Build your profile',
    desc: 'A structured intelligence profile is created, separating verified facts from inferences, with confidence scores on every field.',
  },
  {
    icon: Radar,
    title: 'Discover opportunities',
    desc: 'Continuous, tool-using search across relevant job boards, ATS platforms, and freelance marketplaces for roles and client work.',
  },
  {
    icon: Target,
    title: 'Match & rank with evidence',
    desc: 'Every match ships with a score, the evidence behind it, and any gaps — never an unexplained number.',
  },
  {
    icon: Send,
    title: 'Apply & reach out',
    desc: 'Tailored applications, proposals, and outreach drafted from your real background — you approve before anything is sent.',
  },
  {
    icon: TrendingUp,
    title: 'Track the pipeline',
    desc: 'Follow-ups, responses, interviews, and offers tracked in one place, with continuous monitoring for what changes next.',
  },
];

const ENTERPRISE_STEPS = [
  {
    icon: ListChecks,
    title: 'Define your requirement',
    desc: 'Role, must-have skills, seniority, location, budget, and timeline — captured directly from you.',
  },
  {
    icon: Bot,
    title: 'AI structures the criteria',
    desc: 'Your requirement is turned into structured search criteria the discovery agents can act on.',
  },
  {
    icon: Search,
    title: 'Discover real talent',
    desc: 'Live, tool-using search across relevant professional sources for candidates who actually match.',
  },
  {
    icon: ShieldCheck,
    title: 'Validate & evaluate',
    desc: 'Profiles are verified and scored against your criteria, with claimed vs. demonstrated skills kept distinct.',
  },
  {
    icon: UserCheck,
    title: 'Shortlist & contact',
    desc: 'Compare ranked candidates side by side, build a shortlist, and reach out — with full evidence attached.',
  },
  {
    icon: Handshake,
    title: 'Interview, offer, hire',
    desc: 'Track the pipeline from first contact through interview, offer, and hire in one workspace.',
  },
];

const TRUST_POINTS = [
  {
    icon: Eye,
    title: 'Fact, inference, or unknown',
    desc: 'Every claim is labeled. AI reasoning is never presented as a verified fact — and nothing is guessed to fill a gap.',
  },
  {
    icon: Layers,
    title: 'Provenance on everything',
    desc: 'Every discovered job, candidate, or company keeps its source, retrieval time, and verification status.',
  },
  {
    icon: CheckCircle2,
    title: 'You approve before it sends',
    desc: 'Applications, proposals, and outreach always pass through a human review gate before anything leaves the platform.',
  },
  {
    icon: ShieldCheck,
    title: 'Zero fabricated data',
    desc: 'No invented salaries, companies, contacts, or statistics — ever. If it isn\u2019t known, it\u2019s shown as unknown.',
  },
];

export default function HomePage() {
  // No fabricated defaults: metrics stay null until the live backend responds,
  // so the UI renders an honest loading/empty state instead of fake numbers.
  const [metrics, setMetrics] = useState<PublicMetrics | null>(null);
  const [metricsError, setMetricsError] = useState(false);
  const { user, profile, avatarUrl, displayName, firstName, completion } = useSession();
  const isLoggedIn = Boolean(user?.email || displayName || avatarUrl);

  useEffect(() => {
    fetch('/api/public/statistics')
      .then((res) => res.json())
      .then((payload) => {
        if (payload?.status === 'success' && payload?.data?.metrics) {
          setMetrics(payload.data.metrics);
        } else {
          setMetricsError(true);
        }
      })
      .catch(() => setMetricsError(true));
  }, []);

  const fmt = (value: number | null | undefined) =>
    metricsError ? '\u2014' : value === null || value === undefined ? '\u2014' : value.toLocaleString();

  const fmtPercent = (value: number | null | undefined) =>
    metricsError ? '\u2014' : value === null || value === undefined ? 'No data yet' : `${value}%`;

  return (
    <div className="min-h-screen bg-[#000000] text-[#f4f4f5] selection:bg-white selection:text-black relative overflow-x-hidden font-sans">
      {/* Ambient background glow */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="w-[800px] h-[800px] bg-red-600/[0.10] blur-[160px] animate-aurora rounded-full absolute -top-40 left-1/4" />
        <div className="w-[650px] h-[650px] bg-blue-600/[0.06] blur-[150px] animate-aurora-red rounded-full absolute top-1/3 -right-40" />
        <div className="w-[500px] h-[500px] bg-emerald-600/[0.04] blur-[140px] animate-aurora rounded-full absolute -bottom-20 left-10" />
      </div>

      {/* HEADER */}
      <header className="fixed top-5 inset-x-0 mx-auto max-w-5xl z-50 px-4">
        <div className="apple-glass-pill px-5 py-3 flex items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-3 group shrink-0">
            {isLoggedIn && avatarUrl ? (
              <div className="w-8 h-8 rounded-full overflow-hidden border-2 border-red-500/80 shadow-[0_0_15px_rgba(239,68,68,0.5)] ring-2 ring-red-500/20 group-hover:scale-105 transition-transform">
                <img src={avatarUrl} alt={displayName || 'Profile'} className="w-full h-full object-cover" />
              </div>
            ) : isLoggedIn && displayName ? (
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-red-600 via-rose-500 to-amber-500 flex items-center justify-center text-white font-mono font-black text-xs shadow-[0_0_15px_rgba(239,68,68,0.4)] ring-2 ring-red-500/20 group-hover:scale-105 transition-transform">
                {(firstName || displayName).charAt(0).toUpperCase()}
              </div>
            ) : (
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-white/90 via-white/70 to-white/40 flex items-center justify-center text-black font-mono font-black text-xs shadow-md shadow-white/10 group-hover:scale-105 transition-transform">
                E
              </div>
            )}
            <span className="font-mono font-bold tracking-tight text-white text-sm hidden sm:inline">
              {isLoggedIn && displayName ? displayName : 'EJICODE_AI'}
            </span>
          </Link>

          <nav className="hidden lg:flex items-center gap-6 text-xs text-zinc-400 font-medium">
            <a href="#individuals" className="hover:text-white transition-colors">Individuals</a>
            <a href="#enterprises" className="hover:text-white transition-colors">Enterprises</a>
            <a href="#how-it-works" className="hover:text-white transition-colors">How it works</a>
            <a href="#trust" className="hover:text-white transition-colors">Trust &amp; Data</a>
          </nav>

          <div className="flex items-center gap-2 shrink-0">
            {isLoggedIn ? (
              <div className="flex items-center gap-2">
                <Link
                  href="/individual/profile"
                  className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full apple-glass-subtle text-xs text-zinc-300 hover:text-white transition-all border border-zinc-700/60"
                >
                  {avatarUrl && (
                    <img src={avatarUrl} alt="Avatar" className="w-4 h-4 rounded-full object-cover border border-red-400" />
                  )}
                  <span className="truncate max-w-[120px] font-medium">{displayName || 'My Profile'}</span>
                </Link>
                <Link
                  href={user?.account_type === 'enterprise' ? '/enterprise/dashboard' : '/individual/dashboard'}
                  className="apple-button-primary px-4 py-1.5 text-xs font-semibold whitespace-nowrap flex items-center gap-1.5 shadow-[0_0_15px_rgba(239,68,68,0.35)]"
                >
                  <span>Career Hub</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            ) : (
              <>
                <Link
                  href="/login?type=individual"
                  className="px-3 py-1.5 text-xs text-zinc-300 hover:text-white transition-colors whitespace-nowrap"
                >
                  Login &middot; Individual
                </Link>
                <Link
                  href="/login?type=enterprise"
                  className="apple-button-primary px-4 py-1.5 text-xs font-semibold whitespace-nowrap"
                >
                  Login &middot; Enterprise
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* HERO */}
      <section className="relative pt-32 sm:pt-40 pb-16 px-4 sm:px-8 lg:px-12 z-10">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full apple-glass-subtle text-xs text-zinc-300 font-medium mb-8 animate-float">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span>One AI platform. Two sides of hiring.</span>
          </div>

          <h1 className="text-4xl sm:text-6xl md:text-7xl font-semibold tracking-tight text-white leading-[1.05]">
            AI that gets people hired,
            <br />
            <span className="text-gradient-apple-glow font-bold">and helps companies hire well.</span>
          </h1>

          <p className="mt-6 text-sm sm:text-lg text-zinc-400 max-w-2xl mx-auto leading-relaxed">
            EJICODE AI runs as a real, tool-using agent workflow &mdash; not a chatbot. It reads your CV or your
            hiring requirement, searches live sources, validates what it finds, and explains every match with
            evidence. Nothing invented, nothing hidden.
          </p>

          {/* LOGGED IN WITH YOUR PROFILE - HERO CARD */}
          {isLoggedIn && (
            <div className="mt-10 max-w-2xl mx-auto apple-glass rounded-3xl p-6 sm:p-7 border border-red-500/40 shadow-[0_0_40px_rgba(239,68,68,0.28)] animate-fade-in-up text-left">
              <div className="flex flex-col sm:flex-row items-center sm:items-start gap-5">
                <div className="relative shrink-0">
                  <div className="w-20 h-20 rounded-full overflow-hidden border-2 border-red-500 shadow-[0_0_22px_rgba(239,68,68,0.55)] ring-4 ring-red-500/20">
                    {avatarUrl ? (
                      <img
                        src={avatarUrl}
                        alt={displayName || 'Profile Avatar'}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-tr from-red-600 via-rose-500 to-amber-500 flex items-center justify-center text-white font-mono font-black text-2xl">
                        {(firstName || displayName || 'U').charAt(0).toUpperCase()}
                      </div>
                    )}
                  </div>
                  <span
                    className="absolute bottom-0.5 right-0.5 w-5 h-5 rounded-full bg-emerald-500 border-2 border-black shadow-[0_0_10px_rgba(16,185,129,0.9)]"
                    title="Active Session"
                  />
                </div>

                <div className="flex-1 text-center sm:text-left min-w-0">
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-500/10 border border-red-500/30 text-[11px] font-bold text-red-400 mb-2 shadow-[0_0_12px_rgba(239,68,68,0.2)]">
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                    Logged in with your profile
                  </div>
                  <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight truncate">
                    {displayName || user?.full_name || 'Candidate Member'}
                  </h2>
                  <p className="text-xs sm:text-sm text-zinc-300 mt-1 truncate">
                    {profile?.title || 'Verified Professional Profile'} {user?.email ? `• ${user.email}` : ''}
                  </p>

                  <div className="mt-3 flex flex-wrap items-center justify-center sm:justify-start gap-2">
                    <span className="apple-glass-subtle px-3 py-1 rounded-full text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5 text-xs font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {completion?.percent !== undefined
                        ? `Profile ${completion.percent}% complete`
                        : 'Profile Active'}
                    </span>
                    <span className="apple-glass-subtle px-3 py-1 rounded-full text-zinc-300 border border-zinc-700/80 font-mono text-[11px]">
                      {user?.account_type === 'enterprise' ? 'Role: Enterprise' : 'Role: Individual Candidate'}
                    </span>
                    {completion?.agent_ready && (
                      <span className="apple-glass-subtle px-2.5 py-1 rounded-full text-blue-400 border border-blue-500/30 text-[11px] font-medium">
                        Agents Ready
                      </span>
                    )}
                  </div>

                  <div className="mt-5 flex flex-wrap items-center justify-center sm:justify-start gap-3">
                    <Link
                      href={user?.account_type === 'enterprise' ? '/enterprise/dashboard' : '/individual/dashboard'}
                      className="apple-button-primary px-5 py-2.5 text-xs font-semibold flex items-center gap-2 shadow-[0_0_20px_rgba(239,68,68,0.4)] hover:shadow-[0_0_25px_rgba(239,68,68,0.6)]"
                    >
                      <span>Continue to Career Hub</span>
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                    <Link
                      href="/individual/profile"
                      className="apple-glass-subtle hover:bg-white/10 px-4 py-2.5 rounded-full text-xs font-medium text-zinc-300 hover:text-white transition-all border border-zinc-700/70"
                    >
                      Manage Profile &amp; Photo
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* DUAL PATH SELECTOR */}
        <div className="max-w-5xl mx-auto mt-14 grid md:grid-cols-2 gap-5">
          {/* INDIVIDUAL PATH */}
          <div id="individuals" className="apple-glass rounded-3xl p-7 sm:p-8 flex flex-col scroll-mt-28">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-blue-500/10 border border-blue-400/20 flex items-center justify-center">
                <Users className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <div className="text-[10px] font-mono uppercase tracking-widest text-blue-400 font-bold">For Individuals</div>
                <h2 className="text-xl font-bold text-white">Get hired or win client work</h2>
              </div>
            </div>

            <p className="mt-4 text-xs sm:text-sm text-zinc-400 leading-relaxed">
              Upload your CV once. The AI understands your skills and experience, then works continuously to
              find real jobs and freelance opportunities that fit &mdash; and helps you approach them.
            </p>

            <ul className="mt-5 space-y-2.5 text-xs text-zinc-300">
              {['CV intelligence, not just storage', 'Live opportunity discovery across 8+ source categories', 'Transparent match scores with evidence', 'Anti-scam &amp; freshness checks on every listing'].map((item) => (
                <li key={item} className="flex items-start gap-2.5">
                  <Check className="w-3.5 h-3.5 text-blue-400 mt-0.5 shrink-0" />
                  <span dangerouslySetInnerHTML={{ __html: item }} />
                </li>
              ))}
            </ul>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              {isLoggedIn ? (
                <Link
                  href="/individual/dashboard"
                  className="apple-button-primary px-6 py-3 text-xs font-semibold flex items-center gap-2 shadow-[0_0_15px_rgba(59,130,246,0.3)]"
                >
                  <Briefcase className="w-4 h-4 text-blue-400" />
                  <span>Enter Career Hub &rarr;</span>
                </Link>
              ) : (
                <>
                  <Link
                    href="/login?type=individual"
                    className="apple-button-primary px-6 py-3 text-xs font-semibold flex items-center gap-2"
                  >
                    <Briefcase className="w-4 h-4" />
                    <span>Login as Individual</span>
                  </Link>
                  <Link
                    href="/register?type=individual"
                    className="text-xs text-zinc-300 hover:text-white underline underline-offset-2 transition-colors"
                  >
                    Create free account
                  </Link>
                </>
              )}
            </div>
          </div>

          {/* ENTERPRISE PATH */}
          <div id="enterprises" className="apple-glass rounded-3xl p-7 sm:p-8 flex flex-col scroll-mt-28">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-emerald-500/10 border border-emerald-400/20 flex items-center justify-center">
                <Building2 className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <div className="text-[10px] font-mono uppercase tracking-widest text-emerald-400 font-bold">For Enterprises</div>
                <h2 className="text-xl font-bold text-white">Find the right people, faster</h2>
              </div>
            </div>

            <p className="mt-4 text-xs sm:text-sm text-zinc-400 leading-relaxed">
              Describe the role or client work you need filled. The AI searches, verifies, and ranks real
              professionals against your actual requirements &mdash; and shows you why each one fits.
            </p>

            <ul className="mt-5 space-y-2.5 text-xs text-zinc-300">
              {['Requirement-driven talent discovery', 'Evidence-based candidate ranking, not a black box', 'Shortlists, comparisons &amp; talent pools', 'Full hiring pipeline: contact &rarr; interview &rarr; offer &rarr; hire'].map((item) => (
                <li key={item} className="flex items-start gap-2.5">
                  <Check className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                  <span dangerouslySetInnerHTML={{ __html: item }} />
                </li>
              ))}
            </ul>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              {isLoggedIn ? (
                <Link
                  href="/enterprise/dashboard"
                  className="apple-button-secondary px-6 py-3 text-xs font-semibold flex items-center gap-2"
                >
                  <Building2 className="w-4 h-4 text-emerald-400" />
                  <span>Enter Enterprise Pipeline &rarr;</span>
                </Link>
              ) : (
                <>
                  <Link
                    href="/login?type=enterprise"
                    className="apple-button-secondary px-6 py-3 text-xs font-semibold flex items-center gap-2"
                  >
                    <Building2 className="w-4 h-4" />
                    <span>Login as Enterprise</span>
                  </Link>
                  <Link
                    href="/register?type=enterprise"
                    className="text-xs text-zinc-300 hover:text-white underline underline-offset-2 transition-colors"
                  >
                    Create organization account
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="max-w-5xl mx-auto mt-6 flex flex-wrap items-center justify-center gap-x-4 gap-y-1.5 text-[11px] sm:text-xs text-zinc-500">
          <KeyRound className="w-3.5 h-3.5" />
          <Link href="/forgot-password" className="hover:text-white underline underline-offset-2 transition-colors">
            Forgot your password?
          </Link>
          <span className="text-zinc-700">&bull;</span>
          <a href="#how-it-works" className="hover:text-white underline underline-offset-2 transition-colors">
            See exactly how it works
          </a>
        </div>
      </section>

      {/* LIVE METRICS STRIP */}
      <section className="px-4 sm:px-8 lg:px-12 pb-6 relative z-10">
        <div className="max-w-5xl mx-auto apple-glass-subtle rounded-2xl p-5 sm:p-6 grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-xl sm:text-2xl font-bold text-white font-mono">{fmt(metrics?.total_opportunities_indexed)}</div>
            <div className="text-[10px] sm:text-[11px] text-zinc-500 font-mono uppercase tracking-wide mt-1">Opportunities Indexed</div>
          </div>
          <div>
            <div className="text-xl sm:text-2xl font-bold text-white font-mono">{fmt(metrics?.total_companies_verified)}</div>
            <div className="text-[10px] sm:text-[11px] text-zinc-500 font-mono uppercase tracking-wide mt-1">Companies Verified</div>
          </div>
          <div>
            <div className="text-xl sm:text-2xl font-bold text-white font-mono">{fmt(metrics?.candidates_matched)}</div>
            <div className="text-[10px] sm:text-[11px] text-zinc-500 font-mono uppercase tracking-wide mt-1">Candidates Matched</div>
          </div>
          <div>
            <div className="text-xl sm:text-2xl font-bold text-white font-mono">{metrics ? metrics.active_sources_count : '\u2014'}</div>
            <div className="text-[10px] sm:text-[11px] text-zinc-500 font-mono uppercase tracking-wide mt-1">Live Source Channels</div>
          </div>
        </div>
        <p className="text-center text-[10px] text-zinc-600 font-mono mt-3">
          Live from the EJICODE AI database &mdash; not marketing copy. Zero activity shows as zero.
        </p>
      </section>

      {/* HOW IT WORKS: SIDE-BY-SIDE COMPARISON */}
      <section id="how-it-works" className="py-24 px-4 sm:px-8 lg:px-12 max-w-6xl mx-auto relative z-10 scroll-mt-16">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <div className="apple-glass-pill px-3 py-1 text-[11px] text-zinc-400 inline-block font-mono mb-3">
            REAL AGENT WORKFLOW, NOT A CHATBOT
          </div>
          <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-white">
            Two workflows. <span className="text-gradient-apple">One intelligence engine.</span>
          </h2>
          <p className="mt-4 text-sm text-zinc-400 leading-relaxed">
            Individuals and enterprises get purpose-built flows &mdash; the same underlying agents discover,
            validate, and rank, but the objective and the dashboard are completely different.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-x-10 gap-y-6">
          <div>
            <div className="flex items-center gap-2 mb-5">
              <Users className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wide">Individual Flow</h3>
            </div>
            <div className="space-y-3">
              {INDIVIDUAL_STEPS.map((step, i) => (
                <div key={step.title} className="apple-glass-subtle rounded-2xl p-4 flex items-start gap-3.5 hover:border-blue-400/30 transition-all">
                  <div className="w-8 h-8 rounded-xl bg-blue-500/10 border border-blue-400/20 flex items-center justify-center shrink-0 text-blue-400 text-[11px] font-mono font-bold">
                    {i + 1}
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white">{step.title}</h4>
                    <p className="text-[11px] text-zinc-400 mt-1 leading-relaxed">{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-5">
              <Building2 className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wide">Enterprise Flow</h3>
            </div>
            <div className="space-y-3">
              {ENTERPRISE_STEPS.map((step, i) => (
                <div key={step.title} className="apple-glass-subtle rounded-2xl p-4 flex items-start gap-3.5 hover:border-emerald-400/30 transition-all">
                  <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-400/20 flex items-center justify-center shrink-0 text-emerald-400 text-[11px] font-mono font-bold">
                    {i + 1}
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white">{step.title}</h4>
                    <p className="text-[11px] text-zinc-400 mt-1 leading-relaxed">{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* TRUST & DATA INTEGRITY */}
      <section id="trust" className="py-24 px-4 sm:px-8 lg:px-12 max-w-6xl mx-auto relative z-10 scroll-mt-16">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <div className="apple-glass-pill px-3 py-1 text-[11px] text-zinc-400 inline-block font-mono mb-3">
            ANTI-FABRICATION BY DESIGN
          </div>
          <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-white">
            If it isn&rsquo;t verified, <span className="text-gradient-apple">it isn&rsquo;t shown as real.</span>
          </h2>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {TRUST_POINTS.map((point) => (
            <div key={point.title} className="apple-glass rounded-2xl p-5">
              <point.icon className="w-5 h-5 text-red-400 mb-3" />
              <h3 className="text-sm font-bold text-white">{point.title}</h3>
              <p className="text-xs text-zinc-400 mt-2 leading-relaxed">{point.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="py-24 px-4 sm:px-8 lg:px-12 max-w-4xl mx-auto text-center relative z-10">
        <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-white">
          Pick your side. The AI does the rest.
        </h2>
        <p className="mt-4 text-sm text-zinc-400 max-w-xl mx-auto">
          Whether you&rsquo;re looking for your next role or your next hire, EJICODE AI works from real data,
          start to finish.
        </p>

        <div className="mt-8 flex flex-wrap justify-center gap-3 sm:gap-4">
          <Link
            href="/login?type=individual"
            className="apple-button-primary px-8 py-3.5 text-sm font-semibold flex items-center gap-2.5"
          >
            <span>Login as Individual</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/login?type=enterprise"
            className="apple-button-secondary px-8 py-3.5 text-sm font-semibold flex items-center gap-2.5"
          >
            <span>Login as Enterprise</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="mt-5 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-xs text-zinc-500">
          <span>No account yet?</span>
          <Link href="/register?type=individual" className="hover:text-white underline underline-offset-2 transition-colors">Sign up as Individual</Link>
          <span className="text-zinc-700">&bull;</span>
          <Link href="/register?type=enterprise" className="hover:text-white underline underline-offset-2 transition-colors">Sign up as Enterprise</Link>
          <span className="text-zinc-700">&bull;</span>
          <Link href="/forgot-password" className="hover:text-white underline underline-offset-2 transition-colors">Forgot password?</Link>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="py-10 px-4 sm:px-8 lg:px-12 border-t border-white/10 relative z-10 text-xs text-zinc-500">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-5">
          <div className="flex flex-wrap items-center justify-center gap-3">
            <div className="w-6 h-6 rounded-full bg-white flex items-center justify-center text-black font-mono font-bold text-xs">
              E
            </div>
            <span className="font-mono font-bold text-white">EJICODE_AI</span>
            <span className="text-zinc-700">&bull;</span>
            <span>&copy; {new Date().getFullYear()} All Rights Reserved.</span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6">
            <Link href="/login?type=individual" className="hover:text-white transition-colors">Login as Individual</Link>
            <Link href="/login?type=enterprise" className="hover:text-white transition-colors">Login as Enterprise</Link>
            <Link href="/forgot-password" className="hover:text-white transition-colors">Forgot Password?</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
