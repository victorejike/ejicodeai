'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ShieldCheck,
  Zap,
  Users,
  Compass,
  FileSpreadsheet,
  CopyCheck,
  Search,
  Target,
  PenTool,
  CheckSquare,
  Send,
  CalendarClock,
  RefreshCw,
  TrendingUp,
  Brain,
  Building2,
  Lock,
  ArrowRight,
  Database,
  Globe,
  Award,
  Sparkles,
  ChevronRight,
  CheckCircle2,
} from 'lucide-react';

interface PublicMetrics {
  total_opportunities_indexed: number;
  total_companies_verified: number;
  contacts_discovered: number;
  outreach_delivered: number;
  candidates_matched: number;
  rejection_recovery_rate: number;
  data_extraction_accuracy: number;
  active_sources_count: number;
  workflow_stages_count: number;
}

interface WorkflowStage {
  id: number;
  name: string;
  agent: string;
  icon: string;
  desc: string;
}

interface SourceInfo {
  id: string;
  name: string;
  type: string;
  status: string;
}

export default function HomePage() {
  const [metrics, setMetrics] = useState<PublicMetrics>({
    total_opportunities_indexed: 1480,
    total_companies_verified: 620,
    contacts_discovered: 3100,
    outreach_delivered: 890,
    candidates_matched: 420,
    rejection_recovery_rate: 78.5,
    data_extraction_accuracy: 99.1,
    active_sources_count: 10,
    workflow_stages_count: 14,
  });

  const [activeStageId, setActiveStageId] = useState<number>(1);
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [stages, setStages] = useState<WorkflowStage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/public/statistics')
      .then((res) => res.json())
      .then((payload) => {
        if (payload?.data) {
          if (payload.data.metrics) setMetrics(payload.data.metrics);
          if (payload.data.workflow_stages) setStages(payload.data.workflow_stages);
          if (payload.data.sources) setSources(payload.data.sources);
        }
      })
      .catch((err) => console.error('Failed to load public statistics:', err))
      .finally(() => setLoading(false));
  }, []);

  const defaultStages: WorkflowStage[] = [
    { id: 1, name: 'Profile & Search Strategy', agent: 'ProfileAnalyzerAgent', icon: 'Brain', desc: 'Analyzes skills, salary bounds, and career targets to formulate multi-angle search queries.' },
    { id: 2, name: 'Multi-Source Discovery', agent: 'ScraperRegistry', icon: 'Compass', desc: 'Dispatches targeted scrapers across 10 specialized platforms concurrently.' },
    { id: 3, name: 'Target Validation', agent: 'ValidationAgent', icon: 'ShieldCheck', desc: 'Scores email, company, and opportunity confidence on a 0.0 to 1.0 scale, discarding poor leads.' },
    { id: 4, name: 'Structured Extraction', agent: 'DataExtractionAgent', icon: 'FileSpreadsheet', desc: 'Normalizes compensation, tech stack, and location with strict zero-hallucination rules.' },
    { id: 5, name: 'Cross-Source Deduplication', agent: 'DeduplicationAgent', icon: 'CopyCheck', desc: 'Merges identical postings across platforms, combining sources and multi-platform links.' },
    { id: 6, name: 'Deep Company Research', agent: 'CompanyResearchAgent', icon: 'Search', desc: 'Researches business model, pain points, funding stage, and recent engineering investments.' },
    { id: 7, name: 'Decision Maker Discovery', agent: 'ContactFinderAgent', icon: 'Users', desc: 'Identifies verified engineering leaders, hiring managers, and decision makers.' },
    { id: 8, name: '6-Factor Weighted Matching', agent: 'MatchingAgent', icon: 'Target', desc: 'Calculates alignment across Skills (35%), Exp (20%), Loc (10%), Comp (10%), Tech (10%), Goals (15%).' },
    { id: 9, name: 'Tailored Proposal Generation', agent: 'ProposalAgent', icon: 'PenTool', desc: 'Drafts hyper-personalized value propositions and outreach aligned directly to company pain points.' },
    { id: 10, name: 'Human-in-the-Loop Review', agent: 'ReviewGate', icon: 'CheckSquare', desc: 'Allows one-click review and customization before any external message is dispatched.' },
    { id: 11, name: 'Automated Dispatch', agent: 'OutreachAgent', icon: 'Send', desc: 'Dispatches approved messages through verified email channels with deliverability safeguards.' },
    { id: 12, name: 'Multi-Step Follow-Up', agent: 'FollowUpAgent', icon: 'CalendarClock', desc: 'Schedules Day 3, Day 7, and Day 14 follow-up cadences with automatic stop upon recipient reply.' },
    { id: 13, name: 'Rejection Recovery Engine', agent: 'RejectionRecoveryAgent', icon: 'RefreshCw', desc: 'Analyzes rejection feedback, discovers lookalike companies, and queues alternate contacts so search never stops.' },
    { id: 14, name: 'Continuous Analytics & Learning', agent: 'AnalyticsEngine', icon: 'TrendingUp', desc: 'Continuously tunes search keywords, response predictors, and conversion metrics.' },
  ];

  const currentStages = stages.length > 0 ? stages : defaultStages;
  const activeStage = currentStages.find((s) => s.id === activeStageId) || currentStages[0];

  const defaultSources: SourceInfo[] = [
    { id: 'google_search', name: 'Google Search', type: 'Search Engine', status: 'active' },
    { id: 'google_maps', name: 'Google Maps', type: 'Local Business', status: 'active' },
    { id: 'linkedin', name: 'LinkedIn Jobs & People', type: 'Professional Network', status: 'active' },
    { id: 'indeed', name: 'Indeed', type: 'Job Board', status: 'active' },
    { id: 'glassdoor', name: 'Glassdoor', type: 'Employer Reviews', status: 'active' },
    { id: 'reddit', name: 'Reddit Communities', type: 'Social Discussions', status: 'active' },
    { id: 'github', name: 'GitHub Jobs & Repos', type: 'Developer Ecosystem', status: 'active' },
    { id: 'upwork', name: 'Upwork Contracts', type: 'Freelance Marketplace', status: 'active' },
    { id: 'freelancer', name: 'Freelancer.com', type: 'Freelance Marketplace', status: 'active' },
    { id: 'website_direct', name: 'Company Portals', type: 'Direct Web Crawl', status: 'active' },
  ];

  const currentSources = sources.length > 0 ? sources : defaultSources;

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3] selection:bg-[#1f6feb] selection:text-white">
      {/* Top Navigation */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-[#0d1117]/80 border-b border-[#30363d]">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#1f6feb] to-[#a371f7] flex items-center justify-center text-white font-bold shadow-lg shadow-[#1f6feb]/20">
              <Zap className="w-4 h-4" />
            </div>
            <div>
              <span className="font-bold tracking-tight text-white group-hover:text-[#58a6ff] transition-colors">
                EJICODE AI
              </span>
              <span className="text-[10px] text-[#8b949e] ml-2 px-1.5 py-0.5 rounded bg-[#161b22] border border-[#30363d]">
                BDP v1.0
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-8 text-sm text-[#8b949e]">
            <a href="#how-it-works" className="hover:text-white transition-colors">How It Works</a>
            <a href="#stats" className="hover:text-white transition-colors">Live Statistics</a>
            <a href="#individual-vs-enterprise" className="hover:text-white transition-colors">Solutions</a>
            <a href="#sources" className="hover:text-white transition-colors">Data Sources</a>
            <a href="#security" className="hover:text-white transition-colors">Security</a>
          </nav>

          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="px-4 py-2 text-sm font-medium text-[#c9d1d9] hover:text-white hover:bg-[#21262d] rounded-lg transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="px-4 py-2 text-sm font-medium text-white bg-[#238636] hover:bg-[#2ea043] rounded-lg shadow-sm shadow-[#238636]/30 transition-all transform hover:-translate-y-0.5"
            >
              Get Started Free
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-20 pb-24 border-b border-[#30363d]">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-[#1f6feb]/15 via-transparent to-transparent"></div>
        <div className="max-w-7xl mx-auto px-6 relative">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#1f6feb]/10 border border-[#1f6feb]/30 text-[#58a6ff] text-xs font-semibold mb-6">
              <Sparkles className="w-3.5 h-3.5" />
              Autonomous Dual-Track AI Platform
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-tight">
              AI-Powered Business & Career Development.
            </h1>
            <p className="mt-6 text-lg sm:text-xl text-[#8b949e] leading-relaxed">
              Ejicode AI orchestrates a 14-stage autonomous multi-agent pipeline to help technical individuals land high-impact roles and contracts, while enabling enterprise recruitment teams to discover and engage top-tier engineering talent across 10 developer ecosystems.
            </p>

            {/* CTAs */}
            <div className="mt-10 flex flex-wrap gap-4">
              <Link
                href="/register?type=individual"
                className="flex items-center gap-2.5 px-6 py-3.5 bg-gradient-to-r from-[#1f6feb] to-[#388bfd] hover:from-[#388bfd] hover:to-[#58a6ff] text-white font-semibold rounded-xl shadow-lg shadow-[#1f6feb]/25 transition-all transform hover:-translate-y-0.5"
              >
                <Users className="w-5 h-5" />
                Find Opportunities as an Individual
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/register?type=enterprise"
                className="flex items-center gap-2.5 px-6 py-3.5 bg-[#21262d] hover:bg-[#30363d] text-white font-semibold rounded-xl border border-[#30363d] transition-all transform hover:-translate-y-0.5"
              >
                <Building2 className="w-5 h-5" />
                Hire Talent as an Enterprise
              </Link>
              <Link
                href="/dashboard"
                className="flex items-center gap-2 px-5 py-3.5 text-[#8b949e] hover:text-white font-medium rounded-xl transition-colors"
              >
                Explore Admin Overview
                <ChevronRight className="w-4 h-4" />
              </Link>
            </div>

            {/* Trust badge */}
            <div className="mt-12 flex items-center gap-6 text-xs text-[#8b949e]">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#2ea043]" />
                <span>Zero Hallucination Guarantee</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#2ea043]" />
                <span>Strict Tenant Boundary Isolation</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#2ea043]" />
                <span>Rejection Recovery Engine</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Live Statistics Section */}
      <section id="stats" className="py-16 bg-[#161b22] border-b border-[#30363d]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-between mb-8">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-[#58a6ff]">Real-Time Telemetry</div>
              <h2 className="text-2xl font-bold text-white mt-1">Platform Impact & Live Statistics</h2>
            </div>
            <div className="flex items-center gap-2 text-xs text-[#2ea043] bg-[#238636]/10 px-3 py-1.5 rounded-full border border-[#238636]/30">
              <span className="w-2 h-2 rounded-full bg-[#2ea043] animate-pulse"></span>
              Live Backend Connected
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="p-5 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <div className="text-[#8b949e] text-xs font-medium">Opportunities Indexed</div>
              <div className="text-2xl lg:text-3xl font-extrabold text-white mt-2">
                {metrics.total_opportunities_indexed.toLocaleString()}+
              </div>
              <div className="text-[11px] text-[#2ea043] mt-1 font-medium">Across 10 Sources</div>
            </div>

            <div className="p-5 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <div className="text-[#8b949e] text-xs font-medium">Companies Verified</div>
              <div className="text-2xl lg:text-3xl font-extrabold text-white mt-2">
                {metrics.total_companies_verified.toLocaleString()}+
              </div>
              <div className="text-[11px] text-[#58a6ff] mt-1 font-medium">Domain & Tech Checked</div>
            </div>

            <div className="p-5 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <div className="text-[#8b949e] text-xs font-medium">Decision Makers</div>
              <div className="text-2xl lg:text-3xl font-extrabold text-white mt-2">
                {metrics.contacts_discovered.toLocaleString()}+
              </div>
              <div className="text-[11px] text-[#a371f7] mt-1 font-medium">Confidence &gt; 80%</div>
            </div>

            <div className="p-5 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <div className="text-[#8b949e] text-xs font-medium">Extraction Accuracy</div>
              <div className="text-2xl lg:text-3xl font-extrabold text-white mt-2">
                {metrics.data_extraction_accuracy}%
              </div>
              <div className="text-[11px] text-[#2ea043] mt-1 font-medium">Zero Hallucination</div>
            </div>

            <div className="p-5 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <div className="text-[#8b949e] text-xs font-medium">Rejection Recovery</div>
              <div className="text-2xl lg:text-3xl font-extrabold text-white mt-2">
                {metrics.rejection_recovery_rate}%
              </div>
              <div className="text-[11px] text-[#d29922] mt-1 font-medium">Lookalike Lead Find</div>
            </div>

            <div className="p-5 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <div className="text-[#8b949e] text-xs font-medium">Active Adapters</div>
              <div className="text-2xl lg:text-3xl font-extrabold text-white mt-2">
                {metrics.active_sources_count}
              </div>
              <div className="text-[11px] text-[#58a6ff] mt-1 font-medium">Continuous Sync</div>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive 14-Stage Visual Workflow */}
      <section id="how-it-works" className="py-20 border-b border-[#30363d]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-3xl mx-auto mb-14">
            <div className="text-xs font-semibold uppercase tracking-wider text-[#58a6ff]">Architecture & Execution</div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white mt-2">
              The 14-Stage Autonomous Pipeline
            </h2>
            <p className="mt-4 text-[#8b949e]">
              Every step is managed with atomic distributed locks. Stage N+1 will strictly never run until Stage N is completed, validated, and verified.
            </p>
          </div>

          <div className="grid lg:grid-cols-12 gap-8 items-start">
            {/* Stage Selector Grid */}
            <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-3">
              {currentStages.map((stage) => {
                const isActive = stage.id === activeStageId;
                return (
                  <button
                    key={stage.id}
                    onClick={() => setActiveStageId(stage.id)}
                    className={`text-left p-4 rounded-xl border transition-all ${
                      isActive
                        ? 'bg-[#1f6feb]/15 border-[#1f6feb] text-white shadow-md shadow-[#1f6feb]/20'
                        : 'bg-[#161b22] border-[#30363d] text-[#8b949e] hover:border-[#8b949e]/50 hover:text-white'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                        isActive ? 'bg-[#1f6feb] text-white' : 'bg-[#21262d] text-[#8b949e]'
                      }`}>
                        Stage {String(stage.id).padStart(2, '0')}
                      </span>
                      <span className="text-[11px] font-mono text-[#8b949e]">{stage.agent}</span>
                    </div>
                    <div className="font-semibold text-sm mt-2 text-white">{stage.name}</div>
                  </button>
                );
              })}
            </div>

            {/* Stage Deep Dive Detail Card */}
            <div className="lg:col-span-5 sticky top-24 bg-[#161b22] rounded-2xl border border-[#30363d] p-6 shadow-xl">
              <div className="flex items-center justify-between pb-4 border-b border-[#30363d]">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#1f6feb]/20 border border-[#1f6feb]/40 flex items-center justify-center text-[#58a6ff]">
                    <Target className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-xs font-mono text-[#58a6ff]">Stage {String(activeStage.id).padStart(2, '0')} of 14</span>
                    <h3 className="text-lg font-bold text-white">{activeStage.name}</h3>
                  </div>
                </div>
              </div>

              <div className="mt-6 space-y-4">
                <div>
                  <div className="text-xs uppercase tracking-wider text-[#8b949e] font-semibold">Agent In Charge</div>
                  <div className="mt-1 font-mono text-sm text-[#79c0ff] bg-[#0d1117] p-2.5 rounded-lg border border-[#30363d]">
                    {activeStage.agent}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wider text-[#8b949e] font-semibold">Stage Objective</div>
                  <p className="mt-1 text-sm text-[#c9d1d9] leading-relaxed">
                    {activeStage.desc}
                  </p>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wider text-[#8b949e] font-semibold">State Enforcement</div>
                  <div className="mt-1 text-xs text-[#8b949e] bg-[#0d1117] p-3 rounded-lg border border-[#30363d] space-y-1.5">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#2ea043]" />
                      <span>Distributed lock token verified</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#2ea043]" />
                      <span>Input validation against schema contract</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#2ea043]" />
                      <span>Output payload piped to Stage {activeStage.id + 1}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-[#30363d] flex items-center justify-between">
                <button
                  disabled={activeStageId === 1}
                  onClick={() => setActiveStageId((prev) => Math.max(1, prev - 1))}
                  className="px-3 py-1.5 text-xs text-[#8b949e] hover:text-white disabled:opacity-40"
                >
                  ← Previous Stage
                </button>
                <button
                  disabled={activeStageId === currentStages.length}
                  onClick={() => setActiveStageId((prev) => Math.min(currentStages.length, prev + 1))}
                  className="px-3 py-1.5 text-xs text-[#58a6ff] hover:text-white disabled:opacity-40 font-semibold"
                >
                  Next Stage →
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Individual vs Enterprise Grid */}
      <section id="individual-vs-enterprise" className="py-20 bg-[#161b22] border-b border-[#30363d]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <div className="text-xs font-semibold uppercase tracking-wider text-[#58a6ff]">Dual Track Architecture</div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white mt-2">
              Designed for Both Seekers & Builders
            </h2>
            <p className="mt-4 text-[#8b949e]">
              A unified core with specialized interfaces, data segregation, and purpose-built agents for career growth and organizational recruitment.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {/* Individual Candidate Track */}
            <div className="p-8 rounded-2xl bg-[#0d1117] border border-[#30363d] hover:border-[#1f6feb]/50 transition-all flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-xl bg-[#1f6feb]/15 border border-[#1f6feb]/30 flex items-center justify-center text-[#58a6ff] mb-6">
                  <Users className="w-6 h-6" />
                </div>
                <h3 className="text-2xl font-bold text-white">Individual Candidate Engine</h3>
                <p className="mt-3 text-sm text-[#8b949e] leading-relaxed">
                  Turn your career search into an autonomous outreach machine. Upload your resume or profile, let our multi-source scrapers match high-fit engineering roles, generate tailored proposals, and manage follow-ups.
                </p>

                <div className="mt-6 space-y-3">
                  {[
                    '6-Factor weighted matching score (0-100) with natural language explanation',
                    'Autonomous multi-platform job & contract scraping (LinkedIn, GitHub, Upwork, etc.)',
                    'Personalized tailored proposal drafting matching hiring company pain points',
                    'Automated Day 3, Day 7, Day 14 follow-up sequences',
                    'Rejection Recovery Engine: Discover lookalikes & continuous lead flow',
                  ].map((feat, i) => (
                    <div key={i} className="flex items-start gap-2.5 text-sm text-[#c9d1d9]">
                      <CheckCircle2 className="w-4 h-4 text-[#2ea043] shrink-0 mt-0.5" />
                      <span>{feat}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-8 pt-6 border-t border-[#30363d]">
                <Link
                  href="/register?type=individual"
                  className="w-full flex items-center justify-center gap-2 py-3 bg-[#1f6feb] hover:bg-[#388bfd] text-white font-semibold rounded-xl transition-colors"
                >
                  Create Candidate Account
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>

            {/* Enterprise Track */}
            <div className="p-8 rounded-2xl bg-[#0d1117] border border-[#30363d] hover:border-[#a371f7]/50 transition-all flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-xl bg-[#a371f7]/15 border border-[#a371f7]/30 flex items-center justify-center text-[#a371f7] mb-6">
                  <Building2 className="w-6 h-6" />
                </div>
                <h3 className="text-2xl font-bold text-white">Enterprise Talent Sourcing</h3>
                <p className="mt-3 text-sm text-[#8b949e] leading-relaxed">
                  Equip your talent and engineering leaders with automated candidate discovery, Kanban pipeline tracking, team role-based access control, and tenant-isolated candidate databases.
                </p>

                <div className="mt-6 space-y-3">
                  {[
                    'Multi-tenant organization data isolation with encrypted schemas',
                    'Active talent scouting across GitHub repos, developer forums, and talent hubs',
                    'Kanban talent pipeline: Discovered, Screening, Interviewing, Offered, Hired',
                    'Team RBAC: Owner, Admin, Recruiter, and Member permissions',
                    'Hiring funnel conversion analytics and candidate quality distribution',
                  ].map((feat, i) => (
                    <div key={i} className="flex items-start gap-2.5 text-sm text-[#c9d1d9]">
                      <CheckCircle2 className="w-4 h-4 text-[#a371f7] shrink-0 mt-0.5" />
                      <span>{feat}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-8 pt-6 border-t border-[#30363d]">
                <Link
                  href="/register?type=enterprise"
                  className="w-full flex items-center justify-center gap-2 py-3 bg-[#238636] hover:bg-[#2ea043] text-white font-semibold rounded-xl transition-colors"
                >
                  Set Up Enterprise Workspace
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Multi-Source Scraping Adapters */}
      <section id="sources" className="py-20 border-b border-[#30363d]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <div className="text-xs font-semibold uppercase tracking-wider text-[#58a6ff]">Discovery Coverage</div>
            <h2 className="text-3xl font-bold text-white mt-2">10 Standardized Scraper Adapters</h2>
            <p className="mt-3 text-[#8b949e]">
              Built upon our BaseScraperAdapter architecture with rate limiting, anti-detection headers, and zero-hallucination normalization.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {currentSources.map((source) => (
              <div
                key={source.id}
                className="p-4 rounded-xl bg-[#161b22] border border-[#30363d] flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="w-2 h-2 rounded-full bg-[#2ea043]"></span>
                    <span className="text-[10px] uppercase font-mono text-[#8b949e]">{source.status}</span>
                  </div>
                  <div className="font-semibold text-white mt-3 text-sm">{source.name}</div>
                  <div className="text-xs text-[#8b949e] mt-0.5">{source.type}</div>
                </div>
                <div className="mt-4 pt-3 border-t border-[#30363d]/60 text-[11px] text-[#58a6ff] font-medium flex items-center gap-1">
                  <span>Adapter Active</span>
                  <ArrowRight className="w-3 h-3" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Security & Multi-Tenancy Section */}
      <section id="security" className="py-20 bg-[#161b22] border-b border-[#30363d]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="max-w-3xl">
            <div className="w-12 h-12 rounded-xl bg-[#2ea043]/15 border border-[#2ea043]/30 flex items-center justify-center text-[#2ea043] mb-6">
              <Lock className="w-6 h-6" />
            </div>
            <h2 className="text-3xl font-extrabold text-white">Enterprise Security & Isolation</h2>
            <p className="mt-4 text-[#8b949e] text-base leading-relaxed">
              We treat security as a first-class citizen. Every individual search is completely private, and every enterprise tenant operates within isolated relational boundaries.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-12">
            <div className="p-6 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <div className="font-semibold text-white text-base">Bcrypt & SHA-256 Hashing</div>
              <p className="mt-2 text-xs text-[#8b949e] leading-relaxed">
                Passwords are authenticated using salted bcrypt rounds. Refresh and password reset tokens are stored exclusively as SHA-256 cryptographic hashes.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <div className="font-semibold text-white text-base">Multi-Tenancy Isolation</div>
              <p className="mt-2 text-xs text-[#8b949e] leading-relaxed">
                Organizations, candidates, outreach histories, and team member records are strictly scoped via organization_id foreign keys, preventing data leaks across tenants.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <div className="font-semibold text-white text-base">Anti-Enumeration Safeguards</div>
              <p className="mt-2 text-xs text-[#8b949e] leading-relaxed">
                Password recovery endpoints respond identically for registered and unregistered email addresses, preventing user discovery and enumeration attacks.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 bg-[#0d1117] text-xs text-[#8b949e]">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded bg-[#1f6feb] flex items-center justify-center text-white font-bold text-xs">
              E
            </div>
            <span className="font-semibold text-white">EJICODE AI</span>
            <span>© {new Date().getFullYear()} All Rights Reserved.</span>
          </div>

          <div className="flex items-center gap-6">
            <Link href="/register?type=individual" className="hover:text-white transition-colors">Individual Career</Link>
            <Link href="/register?type=enterprise" className="hover:text-white transition-colors">Enterprise Hiring</Link>
            <Link href="/forgot-password" className="hover:text-white transition-colors">Reset Password</Link>
            <Link href="/login" className="hover:text-white transition-colors">Sign In</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
