'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  User,
  Briefcase,
  Target,
  FileText,
  CalendarClock,
  RefreshCw,
  Send,
  CheckCircle2,
  Sparkles,
  ArrowRight,
  ChevronRight,
  TrendingUp,
  AlertCircle,
  Clock,
  Compass,
  Building2,
  Search,
  ShieldCheck,
  Zap,
  Activity,
  Award,
  Sliders,
  Layers,
  Check,
  BookOpen,
  MessageSquare,
  Flame,
  Radio,
  ExternalLink,
  UploadCloud,
  FileUp,
} from 'lucide-react';
import AgentEventFeed, { AgentEvent } from '@/components/AgentEventFeed';
import { PipelineStage } from '@/components/PipelineProgress';
import ProfileGate from '@/components/ProfileGate';
import OpportunityDetailModal from '@/components/OpportunityDetailModal';
import { Button } from '@/components/ui';
import { useSession } from '@/lib/useSession';

export default function IndividualDashboard() {
  const router = useRouter();
  // Identity and the profile gate come from one shared hook, so the greeting,
  // the checklist and the disabled "run" button can never disagree.
  const {
    completion,
    firstName,
    displayName,
    avatarUrl,
    agentReady,
    gateReason,
    loading: sessionLoading,
    refresh: refreshSession,
  } = useSession();
  const [pipelineStages, setPipelineStages] = useState<PipelineStage[]>([]);
  const [gateMessage, setGateMessage] = useState<string | null>(null);
  const lastCompletedRunRef = useRef<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'matches' | 'companies' | 'marketing' | 'rejection' | 'search_config' | 'profile'>('matches');
  const [pipelineType, setPipelineType] = useState<'employment' | 'freelance'>('employment');
  const [selectedOppForModal, setSelectedOppForModal] = useState<any | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  // Hero KPI & Hiring Progress Pipeline: starts at zero. Real counts are populated
  // from /v1/individual/dashboard-stats (hiring_pipeline) - never fabricated.
  const [hiringPipeline, setHiringPipeline] = useState({
    discovered: 0,
    matched: 0,
    applied: 0,
    contacted: 0,
    responded: 0,
    interviews: 0,
    offers: 0,
  });

  const [stats, setStats] = useState<{
    profile_completion_percentage: number;
    active_matches: number;
    applications_sent: number;
    scheduled_follow_ups: number;
    rejections_recovered: number;
    average_match_score: number | null;
    candidate_title: string | null;
    candidate_name: string | null;
  }>({
    profile_completion_percentage: 0,
    active_matches: 0,
    applications_sent: 0,
    scheduled_follow_ups: 0,
    rejections_recovered: 0,
    average_match_score: null,
    candidate_title: null,
    candidate_name: null,
  });

  // Profile data
  const [profile, setProfile] = useState<any>(null);
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [editFullName, setEditFullName] = useState('');
  const [editTitle, setEditTitle] = useState('');
  const [editBio, setEditBio] = useState('');
  const [editSkills, setEditSkills] = useState('');
  const [editLocation, setEditLocation] = useState('');
  const [editSalaryMin, setEditSalaryMin] = useState<number | ''>('');
  const [editSalaryMax, setEditSalaryMax] = useState<number | ''>('');
  const [editGoals, setEditGoals] = useState('');

  // Continuous Search Config
  // Seeded from this user's saved config and profile. The salary band, job types
  // and industries start empty on purpose: pre-filling someone else's numbers is
  // how a search ends up matching a career that isn't theirs.
  const [searchConfig, setSearchConfig] = useState<{
    search_frequency: string;
    continuous_search_active: boolean;
    job_types: string[];
    locations: string[];
    salary_min: number | '';
    salary_max: number | '';
    salary_currency: string;
    industries: string[];
    remote_preference: string;
  }>({
    search_frequency: 'daily',
    continuous_search_active: true,
    job_types: [],
    locations: [],
    salary_min: '',
    salary_max: '',
    salary_currency: 'USD',
    industries: [],
    remote_preference: 'remote',
  });
  const [isUpdatingConfig, setIsUpdatingConfig] = useState(false);
  const [configMessage, setConfigMessage] = useState<string | null>(null);

  // Resume parse & file upload
  const [resumeText, setResumeText] = useState('');
  const [isParsingResume, setIsParsingResume] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [uploadedFileInfo, setUploadedFileInfo] = useState<any>(null);
  const [parseMessage, setParseMessage] = useState<string | null>(null);

  // Opportunities
  const [matches, setMatches] = useState<any[]>([]);
  const [isLoadingMatches, setIsLoadingMatches] = useState(false);
  const [isMatching, setIsMatching] = useState(false);
  const [applyMessage, setApplyMessage] = useState<string | null>(null);

  // Companies You Should Approach
  const [companiesToApproach, setCompaniesToApproach] = useState<any[]>([]);
  const [isLoadingCompanies, setIsLoadingCompanies] = useState(false);

  // Self-Marketing Engine
  const [marketingMaterials, setMarketingMaterials] = useState<any>(null);
  const [isGeneratingMarketing, setIsGeneratingMarketing] = useState(false);
  const [marketingTargetCompany, setMarketingTargetCompany] = useState('');

  // Rejections
  const [rejectionOppId, setRejectionOppId] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');
  const [rejectionLogs, setRejectionLogs] = useState<any[]>([]);
  const [isProcessingRejection, setIsProcessingRejection] = useState(false);
  const [recoveryOutput, setRecoveryOutput] = useState<any>(null);

  useEffect(() => {
    const t = localStorage.getItem('token');
    setToken(t);
  }, []);

  const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

  const apiFetch = async (path: string, options?: RequestInit) => {
    try {
      const res = await fetch(`/api/individual${path}`, options);
      if (res.ok) return res;
    } catch {
      // fallback to direct backend endpoint
    }
    return fetch(`http://localhost:8000/v1/individual${path}`, options);
  };

  const fetchDashboardData = async () => {
    if (!token) return;
    try {
      const statsRes = await apiFetch('/dashboard-stats', {
        headers: authHeaders,
      });
      if (statsRes.ok) {
        const d = await statsRes.json();
        if (d.data) {
          setStats(d.data);
          if (d.data.hiring_pipeline) {
            setHiringPipeline(d.data.hiring_pipeline);
          }
        }
      }

      const profRes = await apiFetch('/profile', {
        headers: authHeaders,
      });
      if (profRes.ok) {
        const d = await profRes.json();
        if (d.profile) {
          // Discovery must never run against an empty profile - if onboarding
          // hasn't been completed yet, send the user back to set it up first.
          if (!d.profile.onboarding_complete) {
            router.replace('/individual/profile');
            return;
          }
          setProfile(d.profile);
          // Never prefill edit fields with fabricated placeholders - a user who
          // saves without touching these fields must not overwrite real (or
          // intentionally empty) data with an invented title/skills/salary.
          setEditFullName(d.profile.full_name || '');
          setEditTitle(d.profile.title || '');
          setEditBio(d.profile.bio || '');
          setEditSkills((d.profile.skills || []).join(', '));
          setEditLocation(d.profile.location || '');
          setEditSalaryMin(d.profile.salary_min ?? '');
          setEditSalaryMax(d.profile.salary_max ?? '');
          setEditGoals(d.profile.career_goals || '');
          if (d.profile.marketing_materials) {
            setMarketingMaterials(d.profile.marketing_materials);
          }
        }
      }

      fetchMatches();
      fetchCompaniesToApproach();
      fetchSearchConfig();

      const rejRes = await apiFetch('/rejections', {
        headers: authHeaders,
      });
      if (rejRes.ok) {
        const d = await rejRes.json();
        setRejectionLogs(d.rejections || []);
      }
    } catch (err) {
      console.error('Error fetching individual dashboard data:', err);
    }
  };

  const fetchMatches = async () => {
    setIsLoadingMatches(true);
    try {
      const url = `/matches?min_score=50&pipeline_type=${pipelineType}`;
      const res = await apiFetch(url, { headers: authHeaders });
      if (res.ok) {
        const d = await res.json();
        setMatches(d.matches || []);
        if (d.matches && d.matches.length > 0 && !rejectionOppId) {
          setRejectionOppId(d.matches[0].id);
        }
      }
    } catch (err) {
      console.error('Error fetching matches:', err);
    } finally {
      setIsLoadingMatches(false);
    }
  };

  const fetchCompaniesToApproach = async () => {
    setIsLoadingCompanies(true);
    try {
      const res = await apiFetch('/companies-to-approach', {
        headers: authHeaders,
      });
      if (res.ok) {
        const d = await res.json();
        setCompaniesToApproach(d.companies || []);
      }
    } catch (err) {
      console.error('Error fetching companies to approach:', err);
    } finally {
      setIsLoadingCompanies(false);
    }
  };

  const fetchSearchConfig = async () => {
    try {
      const res = await apiFetch('/search-config', {
        headers: authHeaders,
      });
      if (res.ok) {
        const d = await res.json();
        // Merge, so a config the backend has not filled in yet keeps the empty
        // shape instead of turning fields into `undefined`.
        if (d.config) setSearchConfig((prev) => ({ ...prev, ...d.config }));
      }
    } catch (err) {
      console.error('Error fetching search config:', err);
    }
  };

  useEffect(() => {
    if (token) {
      fetchDashboardData();
    }
  }, [token, pipelineType]);

  // Anything the saved search config leaves blank falls back to what the user
  // actually put in their profile - not to a made-up band.
  useEffect(() => {
    if (!profile) return;
    setSearchConfig((prev) => ({
      ...prev,
      salary_min: prev.salary_min === '' ? profile.salary_min ?? '' : prev.salary_min,
      salary_max: prev.salary_max === '' ? profile.salary_max ?? '' : prev.salary_max,
      salary_currency: prev.salary_currency || profile.salary_currency || 'USD',
      job_types: prev.job_types.length ? prev.job_types : profile.job_types ?? [],
      locations: prev.locations.length ? prev.locations : profile.preferred_locations ?? [],
      remote_preference: prev.remote_preference || profile.remote_preference || 'remote',
    }));
  }, [profile]);

  // The declared stage list, so the hand-off strip is visible (greyed out)
  // before the first run rather than appearing out of nowhere mid-chain.
  useEffect(() => {
    if (!token) return;
    (async () => {
      try {
        const res = await apiFetch('/pipeline?limit=1', { headers: authHeaders });
        if (!res.ok) return;
        const d = await res.json();
        if (Array.isArray(d.stages) && d.stages.length) setPipelineStages(d.stages);
      } catch {
        // Not fatal: the strip fills in from the run's own events.
      }
    })();
  }, [token]);

  /**
   * Runs the real agent chain, not just a re-read of stored rows:
   * profile analysis -> discovery -> extraction -> validation -> dedup ->
   * matching -> CV -> contact -> proposal. Each stage's output is the next
   * stage's input, and every step reports on the live feed below.
   */
  const handleTriggerSearch = async () => {
    setIsMatching(true);
    setApplyMessage(null);
    setGateMessage(null);
    try {
      const res = await apiFetch('/pipeline/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ trigger: 'manual', background: true }),
      });
      const body = await res.json().catch(() => null);

      if (res.status === 428) {
        setGateMessage(
          body?.detail?.message ||
            'Finish your profile before the agents can run - they search using your data.'
        );
        refreshSession();
        return;
      }
      if (!res.ok) {
        setApplyMessage(
          body?.detail?.message || body?.detail || 'The agent run could not be started.'
        );
        return;
      }

      if (Array.isArray(body?.stages) && body.stages.length) {
        setPipelineStages(body.stages);
      } else if (Array.isArray(body?.stages_declared)) {
        setPipelineStages(body.stages_declared);
      }
      setApplyMessage(
        body?.message ||
          'Agents are running. Watch the stage strip below - results refresh when the chain finishes.'
      );

      // An inline run has already finished by the time it responds.
      if (body?.status && body.status !== 'queued') {
        await fetchMatches();
        await fetchDashboardData();
      }
    } catch (err) {
      console.error(err);
      setApplyMessage('The agent run could not be started.');
    } finally {
      setIsMatching(false);
    }
  };

  /** Refresh the matches as soon as the chain reports it is done. */
  const handleAgentEvents = (events: AgentEvent[]) => {
    for (let i = events.length - 1; i >= 0; i -= 1) {
      const event = events[i];
      if (event.event_type !== 'pipeline.completed') continue;
      if (event.id && event.id !== lastCompletedRunRef.current) {
        lastCompletedRunRef.current = event.id;
        fetchMatches();
        fetchDashboardData();
      }
      return;
    }
  };

  const handleApply = async (oppId: string, title: string) => {
    try {
      const res = await apiFetch('/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({
          opportunity_id: oppId,
          custom_note: `High alignment application for ${title}.`,
        }),
      });
      if (res.ok) {
        setApplyMessage(`Application outreach dispatched! Day 3, 7, and 14 follow-ups scheduled.`);
        setHiringPipeline((prev) => ({ ...prev, applied: prev.applied + 1 }));
        fetchDashboardData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleGenerateMarketing = async () => {
    setIsGeneratingMarketing(true);
    try {
      const res = await apiFetch('/marketing/materials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({
          company_name: marketingTargetCompany || 'High-Growth Tech Startup',
        }),
      });
      if (res.ok) {
        const d = await res.json();
        setMarketingMaterials(d.marketing_materials);
      }
    } catch (err) {
      console.error('Error generating marketing materials:', err);
    } finally {
      setIsGeneratingMarketing(false);
    }
  };

  const handleUpdateSearchConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdatingConfig(true);
    setConfigMessage(null);
    try {
      const res = await apiFetch('/search-config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(searchConfig),
      });
      if (res.ok) {
        setConfigMessage('Continuous search schedule updated. Fleet will search on configured intervals.');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsUpdatingConfig(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploadingFile(true);
    setParseMessage(null);
    setUploadedFileInfo(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      let res = await fetch('/api/individual/cv/upload', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      if (!res.ok) {
        res = await fetch('http://localhost:8000/v1/individual/cv/upload', {
          method: 'POST',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        });
      }

      const d = await res.json();
      if (res.ok) {
        setUploadedFileInfo(d);
        setParseMessage(
          `Ingested ${d.filename}: Extracted ${d.extracted_skills?.length || 0} skills, ${d.experience_years || 0} yrs experience. ${d.discovered_opportunities_count || 0} live opportunities matched!`
        );
        fetchDashboardData();
        refreshSession();
      } else {
        setParseMessage(`Upload error: ${d.detail || d.error || 'Failed to process document'}`);
      }
    } catch (err: any) {
      setParseMessage(`Network error uploading CV: ${err?.message}`);
    } finally {
      setIsUploadingFile(false);
    }
  };

  const handleParseResume = async () => {
    if (!resumeText.trim()) return;
    setIsParsingResume(true);
    setParseMessage(null);
    try {
      const res = await apiFetch('/profile/resume-parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ resume_text: resumeText }),
      });
      const d = await res.json();
      if (res.ok) {
        setParseMessage(`Parsed ${d.extracted_skills?.length || 0} skills: ${d.extracted_skills?.join(', ')}`);
        fetchDashboardData();
        refreshSession();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsParsingResume(false);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const skillsArray = editSkills.split(',').map((s) => s.trim()).filter(Boolean);
      const res = await apiFetch('/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({
          full_name: editFullName || undefined,
          title: editTitle,
          bio: editBio,
          skills: skillsArray,
          location: editLocation || undefined,
          salary_min: editSalaryMin === '' ? null : Number(editSalaryMin),
          salary_max: editSalaryMax === '' ? null : Number(editSalaryMax),
          career_goals: editGoals,
        }),
      });
      if (res.ok) {
        setIsEditingProfile(false);
        fetchDashboardData();
        refreshSession();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleRejectionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectionOppId || !rejectionReason.trim()) return;
    setIsProcessingRejection(true);
    try {
      const res = await apiFetch('/rejections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({
          opportunity_id: rejectionOppId,
          rejection_reason: rejectionReason,
        }),
      });
      const d = await res.json();
      if (res.ok) {
        setRecoveryOutput(d);
        setRejectionReason('');
        fetchDashboardData();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsProcessingRejection(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Banner & Control Bar */}
      <div className="p-6 md:p-8 rounded-3xl apple-glass relative overflow-hidden flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="absolute top-0 right-0 w-96 h-96 bg-red-600/10 blur-[90px] pointer-events-none rounded-full" />

        <div>
          <div className="flex items-center gap-2.5 text-xs font-bold uppercase tracking-widest text-[var(--accent)] font-mono">
            <span className="w-2 h-2 rounded-full bg-[var(--accent)] animate-pulse" />
            <span>Autonomous Placement Fleet</span>
          </div>
          <div className="flex items-center gap-4 mt-2">
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt="Profile"
                className="w-12 h-12 rounded-full object-cover border-2 border-red-500/50 shadow-md shadow-red-500/20 shrink-0"
              />
            ) : (
              <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-red-600 to-rose-400 flex items-center justify-center font-bold text-white text-lg shadow-md shrink-0">
                {(firstName || displayName || 'U').charAt(0).toUpperCase()}
              </div>
            )}
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-[var(--text)] tracking-tight">
                {sessionLoading ? (
                  <span className="skeleton-shimmer inline-block h-8 w-64 rounded align-middle" />
                ) : firstName || displayName ? (
                  <>Welcome, {firstName || displayName}</>
                ) : (
                  <>Welcome</>
                )}
              </h1>
              <p className="text-xs sm:text-sm text-[var(--text-muted)] mt-0.5 max-w-2xl leading-relaxed">
                {agentReady
                  ? 'Your agents search with your own profile, hand each result to the next agent in the chain, and build an ATS-safe CV for the roles that fit.'
                  : 'Edit your profile to get the best results — the agents search using your data, so what is missing there is what they cannot look for.'}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Pipeline Switcher */}
          <div className="flex apple-glass-subtle p-1 rounded-full">
            <button
              onClick={() => setPipelineType('employment')}
              className={`px-4 py-2 text-xs font-semibold rounded-full transition-all ${
                pipelineType === 'employment'
                  ? 'bg-white text-black shadow-md'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              Direct Placements
            </button>
            <button
              onClick={() => setPipelineType('freelance')}
              className={`px-4 py-2 text-xs font-semibold rounded-full transition-all ${
                pipelineType === 'freelance'
                  ? 'bg-white text-black shadow-md'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              Client Contracts
            </button>
          </div>

          <Link
            href="/individual/profile"
            className="apple-button-secondary px-5 py-3 text-xs font-semibold flex items-center gap-2"
          >
            <User className="w-4 h-4" />
            <span>My Profile</span>
          </Link>

          <Link
            href="/individual/cv-builder"
            className="apple-button-secondary px-5 py-3 text-xs font-semibold flex items-center gap-2"
          >
            <FileText className="w-4 h-4" />
            <span>ATS CV</span>
          </Link>

          <Button
            onClick={handleTriggerSearch}
            loading={isMatching}
            disabledReason={
              !sessionLoading && !agentReady
                ? gateReason ?? 'Finish your profile before the agents can run.'
                : undefined
            }
            icon={<RefreshCw className="w-4 h-4" />}
          >
            {isMatching ? 'Running agents…' : 'Run my agents'}
          </Button>
        </div>
      </div>

      {/* The gate the user has to clear, and the exact fields still missing. */}
      <ProfileGate completion={completion} loading={sessionLoading} />

      {gateMessage && (
        <div className="rounded-2xl border border-[var(--border-red)] bg-[var(--accent-light)] px-4 py-3 text-xs text-[var(--text)]">
          {gateMessage}{' '}
          <Link href="/individual/profile" className="underline">
            Open your profile
          </Link>
        </div>
      )}

      {applyMessage && (
        <div className="p-4 rounded-2xl bg-emerald-950/40 border border-emerald-500/30 flex items-center gap-3 text-emerald-300 text-xs backdrop-blur-xl">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <div className="font-semibold">{applyMessage}</div>
        </div>
      )}

      {/* TOP BENTO TILES (4 KPI Modules) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI Tile 1: Discovered Opportunities */}
        <div className="p-5 rounded-3xl apple-glass hover:border-white/20 transition-all flex flex-col justify-between group">
          <div>
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-zinc-400 font-medium">DISCOVERED LEADS</span>
              <span className="apple-glass-pill px-2.5 py-0.5 text-zinc-300 text-[10px] font-bold">
                8 CHANNELS
              </span>
            </div>
            <div className="text-3xl font-bold text-white mt-3 font-mono">
              {hiringPipeline.discovered}
            </div>
            <div className="text-xs text-zinc-500 font-medium mt-1 flex items-center gap-1 font-mono">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>Live count from your discovery pipeline</span>
            </div>
          </div>
        </div>

        {/* KPI Tile 2: Match Quality Alignment */}
        <div className="p-5 rounded-3xl apple-glass hover:border-white/20 transition-all flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-zinc-400 font-medium">ALIGNMENT FIT</span>
              <span className="apple-glass-pill px-2.5 py-0.5 text-emerald-400 text-[10px] font-bold">
                6-FACTOR
              </span>
            </div>
            <div className="text-3xl font-bold text-white mt-3 font-mono">
              {stats.average_match_score != null ? `${stats.average_match_score}%` : '—'}
            </div>
            <div className="text-xs text-zinc-400 mt-1">
              Skills, stack, budget &amp; seniority
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-white/10">
            <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-red-600 to-rose-400 rounded-full" style={{ width: `${stats.average_match_score ?? 0}%` }} />
            </div>
          </div>
        </div>

        {/* KPI Tile 3: Applications & Outreach */}
        <div className="p-5 rounded-3xl apple-glass hover:border-white/20 transition-all flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-zinc-400 font-medium">DISPATCHED OUTREACH</span>
              <span className="apple-glass-pill px-2.5 py-0.5 text-red-400 text-[10px] font-bold">
                TRUTHFUL
              </span>
            </div>
            <div className="text-3xl font-bold text-white mt-3 font-mono">
              {hiringPipeline.applied} Sent
            </div>
            <div className="text-xs text-zinc-400 mt-1">
              {stats.scheduled_follow_ups} follow-up sequences active
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-[11px] font-mono">
            <span className="text-zinc-500">Cadence: Day 3, 7, 14</span>
            <span className="text-white font-bold">{hiringPipeline.responded} Inbound Replies</span>
          </div>
        </div>

        {/* KPI Tile 4: Offers & Outcome Target */}
        <div className="p-5 rounded-3xl apple-glass hover:border-red-500/30 transition-all flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-red-600/10 blur-[40px] pointer-events-none rounded-full" />
          <div>
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-red-400 font-bold">PLACEMENT TARGET</span>
              <div className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
            </div>
            <div className="text-3xl font-bold text-white mt-3 font-mono">
              {hiringPipeline.interviews} Client Calls
            </div>
            <div className="text-xs text-zinc-300 font-semibold mt-1">
              {hiringPipeline.offers} Contract Offered
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-[11px] font-mono text-zinc-400">
            <span>Continuity: 24/7</span>
            <span className="text-white font-bold">Goal: Get Hired</span>
          </div>
        </div>
      </div>

      {/* MAIN ASYMMETRICAL BENTO GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* MAIN BENTO SECTION (COL-8) */}
        <div className="lg:col-span-8 space-y-6">
          {/* Bento Tabs Header */}
          <div className="p-1.5 rounded-full apple-glass flex gap-1 overflow-x-auto">
            <button
              onClick={() => setActiveTab('matches')}
              className={`px-4 py-2 rounded-full text-xs font-semibold transition-all flex items-center gap-2 whitespace-nowrap ${
                activeTab === 'matches'
                  ? 'bg-white text-black shadow-md'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              <Briefcase className="w-3.5 h-3.5" />
              <span>Opportunities ({matches.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('companies')}
              className={`px-4 py-2 rounded-full text-xs font-semibold transition-all flex items-center gap-2 whitespace-nowrap ${
                activeTab === 'companies'
                  ? 'bg-white text-black shadow-md'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              <Building2 className="w-3.5 h-3.5" />
              <span>Proactive Scout ({companiesToApproach.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('marketing')}
              className={`px-4 py-2 rounded-full text-xs font-semibold transition-all flex items-center gap-2 whitespace-nowrap ${
                activeTab === 'marketing'
                  ? 'bg-white text-black shadow-md'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Self-Marketing</span>
            </button>

            <button
              onClick={() => setActiveTab('rejection')}
              className={`px-4 py-2 rounded-full text-xs font-semibold transition-all flex items-center gap-2 whitespace-nowrap ${
                activeTab === 'rejection'
                  ? 'bg-white text-black shadow-md'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Rejection Radar</span>
            </button>

            <button
              onClick={() => setActiveTab('search_config')}
              className={`px-4 py-2 rounded-full text-xs font-semibold transition-all flex items-center gap-2 whitespace-nowrap ${
                activeTab === 'search_config'
                  ? 'bg-white text-black shadow-md'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              <Sliders className="w-3.5 h-3.5" />
              <span>Continuous Config</span>
            </button>

            <button
              onClick={() => setActiveTab('profile')}
              className={`px-4 py-2 rounded-full text-xs font-semibold transition-all flex items-center gap-2 whitespace-nowrap ${
                activeTab === 'profile'
                  ? 'bg-white text-black shadow-md'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              <User className="w-3.5 h-3.5" />
              <span>Profile</span>
            </button>
          </div>

          {/* Real-time Agent Event Stream */}
          <div className="mb-6">
            <AgentEventFeed
              userId={profile?.user_id}
              title="Live Autonomous Placement Engine"
              stages={pipelineStages}
              onEvents={handleAgentEvents}
            />
          </div>

          {/* TAB 1: Matched Opportunities */}
          {activeTab === 'matches' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2 font-mono">
                    <span>Verified High-Quality Opportunities</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/30">
                      {pipelineType === 'employment' ? 'Employment Pipeline' : 'Freelance Pipeline'}
                    </span>
                  </h3>
                  <div className="text-xs text-[#9ca3af] mt-0.5">
                    Scored via Source Reliability + ATS Freshness + Anti-Scam Shield
                  </div>
                </div>
              </div>

              {isLoadingMatches ? (
                <div className="p-16 rounded-3xl bg-[#0e0e14]/80 border border-white/[0.08] text-center text-[#9ca3af] animate-pulse">
                  Scanning 8 source categories &amp; executing 6-factor alignment…
                </div>
              ) : matches.length === 0 ? (
                <div className="p-12 rounded-3xl bg-[#0e0e14]/80 border border-white/[0.08] text-center space-y-3">
                  <Compass className="w-8 h-8 text-red-400 mx-auto" />
                  <div className="text-white font-bold">No active opportunities indexed yet</div>
                  <p className="text-xs text-[#9ca3af]">Click &quot;Run Career Search&quot; above to discover leads across 8 source categories.</p>
                </div>
              ) : (
                <div className="grid gap-4">
                  {matches.map((opp) => (
                    <div
                      key={opp.id}
                      onClick={() => {
                        setSelectedOppForModal(opp);
                        setIsDetailModalOpen(true);
                      }}
                      className="p-6 rounded-3xl bg-[#0e0e14]/80 border border-white/[0.08] hover:border-red-500/40 transition-all hover:shadow-[0_0_30px_rgba(239,68,68,0.12)] backdrop-blur-2xl space-y-4 group cursor-pointer"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                        <div className="space-y-2 flex-1">
                          <div className="flex items-center gap-2.5 flex-wrap">
                            <span className="text-base font-bold text-white group-hover:text-red-300 transition-colors">
                              {opp.title}
                            </span>
                            <span className="px-2.5 py-0.5 text-xs font-mono font-black rounded-lg bg-red-500/15 text-red-400 border border-red-500/30">
                              {opp.score || opp.match_score || 95}% ATS Fit
                            </span>
                            <span className="px-2.5 py-0.5 text-[10px] rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono flex items-center gap-1 font-bold">
                              <ShieldCheck className="w-3 h-3" />
                              {opp.safety_status || 'SAFE'} ({opp.verification_confidence || 95}% Conf)
                            </span>
                            <span className="px-2 py-0.5 text-[10px] rounded-lg bg-white/[0.04] text-[#9ca3af] font-mono">
                              {opp.location_type || opp.location || 'Remote'}
                            </span>
                            <span className="px-2.5 py-0.5 text-[10px] rounded-lg bg-red-500/10 text-red-300 font-mono font-semibold border border-red-500/20">
                              Source: {opp.source_platform || 'Verified Portal'}
                            </span>
                            {opp.source_url && (
                              <a
                                href={opp.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                className="text-blue-400 hover:text-blue-300 font-mono text-[10px] flex items-center gap-1 hover:underline bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20"
                              >
                                <span>Original Job</span>
                                <ExternalLink className="w-2.5 h-2.5" />
                              </a>
                            )}
                          </div>

                          <div className="text-xs text-[#9ca3af] flex items-center gap-3 flex-wrap">
                            <span className="text-white font-semibold flex items-center gap-1">
                              <Building2 className="w-3.5 h-3.5 text-red-400" />
                              {opp.company_name}
                            </span>
                            <span>•</span>
                            <span>{opp.company_industry || 'Technology'}</span>
                            <span>•</span>
                            <span className="text-emerald-400 font-mono font-semibold">
                              {opp.salary_min && opp.salary_max
                                ? `$${(opp.salary_min / 1000).toFixed(0)}k - $${(opp.salary_max / 1000).toFixed(0)}k`
                                : 'Competitive Market'}
                            </span>
                            {opp.all_sources && opp.all_sources.length > 1 && (
                              <span className="text-emerald-400 font-mono text-[10px] bg-emerald-500/10 px-2 py-0.5 rounded">
                                {opp.all_sources.length} sources deduplicated
                              </span>
                            )}
                          </div>

                          {/* Tech Stack Required */}
                          {opp.tech_required && opp.tech_required.length > 0 && (
                            <div className="flex items-center gap-1.5 flex-wrap pt-1">
                              <span className="text-[10px] font-mono text-zinc-500 font-semibold">Tech:</span>
                              {opp.tech_required.slice(0, 7).map((tech: string, i: number) => (
                                <span
                                  key={i}
                                  className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-white/[0.04] text-zinc-300 border border-white/[0.06]"
                                >
                                  {tech}
                                </span>
                              ))}
                            </div>
                          )}

                          {/* Brief description preview */}
                          {opp.description && (
                            <p className="text-xs text-zinc-400 line-clamp-2 leading-relaxed pt-1">
                              {opp.description}
                            </p>
                          )}
                        </div>

                        <div className="shrink-0 flex sm:flex-col items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedOppForModal(opp);
                              setIsDetailModalOpen(true);
                            }}
                            className="px-5 py-2.5 bg-gradient-to-r from-red-600 to-rose-600 hover:from-rose-600 hover:to-red-600 text-white text-xs font-bold rounded-xl flex items-center gap-2 shadow-md shadow-red-600/30 hover:shadow-red-600/50 transition-all transform hover:-translate-y-0.5 cursor-pointer"
                          >
                            <Sparkles className="w-3.5 h-3.5" />
                            <span>Draft Tailored Outreach</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: Companies You Should Approach */}
          {activeTab === 'companies' && (
            <div className="space-y-4">
              <div className="p-6 rounded-3xl bg-[#0e0e14]/80 border border-white/[0.08] backdrop-blur-2xl">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-red-400" />
                  <span>Proactive Scouting — Companies You Should Approach</span>
                </h3>
                <p className="text-xs text-[#9ca3af] mt-1">
                  Target tech organizations based on recent funding, product launches, or tech stack alignment where your capabilities add value before formal job openings are listed.
                </p>
              </div>

              {isLoadingCompanies ? (
                <div className="p-12 text-center text-[#9ca3af] animate-pulse">Analyzing tech organizations &amp; funding signals…</div>
              ) : companiesToApproach.length === 0 ? (
                <div className="p-8 rounded-3xl bg-[#0e0e14] border border-white/[0.08] text-center">
                  <Building2 className="w-8 h-8 text-[#9ca3af] mx-auto mb-2" />
                  <div className="text-white font-medium">No proactive company targets logged yet</div>
                </div>
              ) : (
                <div className="grid gap-4">
                  {companiesToApproach.map((c, idx) => (
                    <div
                      key={idx}
                      className="p-6 rounded-3xl bg-[#0e0e14]/80 border border-white/[0.08] hover:border-red-500/40 transition-all backdrop-blur-2xl space-y-3"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-3">
                            <span className="text-base font-bold text-white">{c.company_name}</span>
                            <span className="px-2.5 py-0.5 text-xs font-mono font-bold rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                              {c.approach_score}% Fit
                            </span>
                            <span className="text-xs text-[#9ca3af]">{c.industry}</span>
                          </div>
                          <p className="text-xs text-[#d1d5db] mt-1.5 leading-relaxed">{c.approach_reason}</p>
                        </div>

                        <div className="shrink-0">
                          <button
                            onClick={() => {
                              setMarketingTargetCompany(c.company_name);
                              setActiveTab('marketing');
                            }}
                            className="px-4 py-2 bg-gradient-to-r from-red-600 to-rose-600 hover:from-rose-600 hover:to-red-600 text-white text-xs font-bold rounded-xl flex items-center gap-1.5 shadow-md shadow-red-600/30"
                          >
                            <Sparkles className="w-3.5 h-3.5" />
                            <span>Generate Pitch</span>
                          </button>
                        </div>
                      </div>

                      <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between text-xs text-[#9ca3af] flex-wrap gap-2">
                        <span>Target Decision-Maker: <strong className="text-white">{c.target_contact_role}</strong></span>
                        <span>Key Matched Skills: <strong className="text-red-400">{c.valuable_skills?.join(', ')}</strong></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: AI Self-Marketing Engine */}
          {activeTab === 'marketing' && (
            <div className="space-y-6">
              <div className="p-6 rounded-3xl bg-[#0e0e14]/80 border border-white/[0.08] backdrop-blur-2xl space-y-4">
                <div className="flex items-center justify-between flex-wrap gap-4">
                  <div>
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-red-400 font-mono">
                      <Sparkles className="w-4 h-4" />
                      Truthful Self-Marketing Engine
                    </div>
                    <h3 className="text-base font-bold text-white mt-1">Verified Candidate Professional Positioning</h3>
                    <p className="text-xs text-[#9ca3af]">
                      Generates bios, resume highlights, portfolio positioning, cover letters, and client proposals with zero fabrication.
                    </p>
                  </div>

                  <button
                    onClick={handleGenerateMarketing}
                    disabled={isGeneratingMarketing}
                    className="px-5 py-2.5 bg-gradient-to-r from-red-600 to-rose-600 hover:from-rose-600 hover:to-red-600 disabled:opacity-50 text-white font-bold rounded-xl text-xs transition-all flex items-center gap-2 shadow-lg shadow-red-600/30"
                  >
                    <Sparkles className={`w-3.5 h-3.5 ${isGeneratingMarketing ? 'animate-spin' : ''}`} />
                    <span>{isGeneratingMarketing ? 'Generating Positioning…' : 'Generate Marketing Pack'}</span>
                  </button>
                </div>

                <div className="flex items-center gap-3">
                  <input
                    type="text"
                    value={marketingTargetCompany}
                    onChange={(e) => setMarketingTargetCompany(e.target.value)}
                    placeholder="Target Company Name (e.g. ScaleVector, Nova Labs AI)"
                    className="w-full sm:w-96 px-3.5 py-2.5 bg-[#08080a] border border-white/[0.08] rounded-xl text-white text-xs focus:outline-none focus:border-red-500"
                  />
                </div>
              </div>

              {marketingMaterials && (
                <div className="grid lg:grid-cols-2 gap-6">
                  {/* Bios */}
                  <div className="p-6 rounded-3xl bg-[#0e0e14]/80 border border-white/[0.08] backdrop-blur-2xl space-y-4">
                    <h4 className="text-sm font-bold text-white flex items-center gap-2">
                      <BookOpen className="w-4 h-4 text-red-400" />
                      <span>Professional Bios</span>
                    </h4>

                    <div className="space-y-3 text-xs">
                      <div className="p-4 rounded-2xl bg-[#08080a] border border-white/[0.06]">
                        <span className="text-[10px] font-mono text-[#9ca3af] uppercase">Short Bio</span>
                        <p className="text-white mt-1 leading-relaxed">{marketingMaterials.bios?.short}</p>
                      </div>
                      <div className="p-4 rounded-2xl bg-[#08080a] border border-white/[0.06]">
                        <span className="text-[10px] font-mono text-[#9ca3af] uppercase">Medium Bio</span>
                        <p className="text-white mt-1 leading-relaxed">{marketingMaterials.bios?.medium}</p>
                      </div>
                      <div className="p-4 rounded-2xl bg-[#08080a] border border-white/[0.06]">
                        <span className="text-[10px] font-mono text-[#9ca3af] uppercase">Value Proposition</span>
                        <p className="text-red-400 mt-1 font-semibold">{marketingMaterials.value_proposition}</p>
                      </div>
                    </div>
                  </div>

                  {/* Proposals & Cover Letters */}
                  <div className="p-6 rounded-3xl bg-[#0e0e14]/80 border border-white/[0.08] backdrop-blur-2xl space-y-4">
                    <h4 className="text-sm font-bold text-white flex items-center gap-2">
                      <MessageSquare className="w-4 h-4 text-emerald-400" />
                      <span>Application &amp; Outreach Pack</span>
                    </h4>

                    <div className="space-y-3 text-xs">
                      <div className="p-4 rounded-2xl bg-[#08080a] border border-white/[0.06]">
                        <span className="text-[10px] font-mono text-[#9ca3af] uppercase">Tailored Cover Letter</span>
                        <p className="text-[#d1d5db] mt-1 whitespace-pre-line leading-relaxed">{marketingMaterials.cover_letter}</p>
                      </div>
                      <div className="p-4 rounded-2xl bg-[#08080a] border border-white/[0.06]">
                        <span className="text-[10px] font-mono text-[#9ca3af] uppercase">Client / Project Proposal</span>
                        <p className="text-[#d1d5db] mt-1 whitespace-pre-line leading-relaxed">{marketingMaterials.freelance_proposal}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: Rejection Intelligence */}
          {activeTab === 'rejection' && (
            <div className="grid lg:grid-cols-2 gap-6">
              <div className="p-6 rounded-3xl bg-[#0e0e14]/80 border border-white/[0.08] backdrop-blur-2xl space-y-4">
                <div>
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-amber-400 font-mono">
                    <RefreshCw className="w-3.5 h-3.5" />
                    Continuous Recovery Engine
                  </div>
                  <h3 className="text-base font-bold text-white mt-1">Log Outcome to Recover Lookalikes</h3>
                  <p className="text-xs text-[#9ca3af] mt-1">
                    A rejection triggers lookalike discovery across similar orgs, adjusts positioning, and continues searching automatically.
                  </p>
                </div>

                <form onSubmit={handleRejectionSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-[#d1d5db] mb-1.5">
                      Select Opportunity
                    </label>
                    <select
                      value={rejectionOppId}
                      onChange={(e) => setRejectionOppId(e.target.value)}
                      className="w-full px-3.5 py-2.5 bg-[#08080a] border border-white/[0.08] rounded-xl text-white text-xs focus:outline-none focus:border-red-500"
                    >
                      {matches.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.title} at {m.company_name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#d1d5db] mb-1.5">
                      Feedback or Rejection Reason
                    </label>
                    <textarea
                      rows={3}
                      required
                      value={rejectionReason}
                      onChange={(e) => setRejectionReason(e.target.value)}
                      placeholder="e.g. Selected internal candidate; commended Python and distributed systems background."
                      className="w-full px-3.5 py-2.5 bg-[#08080a] border border-white/[0.08] rounded-xl text-white text-xs focus:outline-none focus:border-red-500"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={isProcessingRejection || !rejectionReason.trim()}
                    className="w-full py-3 bg-amber-500 hover:bg-amber-400 text-black font-black rounded-xl text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50 shadow-md shadow-amber-500/20"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isProcessingRejection ? 'animate-spin' : ''}`} />
                    <span>{isProcessingRejection ? 'Processing Feedback…' : 'Trigger Lookalike Search'}</span>
                  </button>
                </form>
              </div>

              <div className="space-y-4">
                {recoveryOutput && (
                  <div className="p-6 rounded-3xl bg-[#08080a] border border-emerald-500/40 space-y-2">
                    <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Lookalike Search Activated</span>
                    </div>
                    <p className="text-xs text-[#d1d5db]">{recoveryOutput.recovery_action_plan}</p>
                  </div>
                )}

                <div className="p-6 rounded-3xl bg-[#0e0e14]/80 border border-white/[0.08] backdrop-blur-2xl">
                  <h4 className="text-sm font-bold text-white mb-3">Rejection Intelligence &amp; Lookalike Log</h4>
                  {rejectionLogs.length === 0 ? (
                    <div className="text-xs text-[#9ca3af]">No rejection records logged yet.</div>
                  ) : (
                    <div className="space-y-3">
                      {rejectionLogs.map((log) => (
                        <div key={log.id} className="p-4 rounded-2xl bg-[#08080a] border border-white/[0.06] text-xs">
                          <div className="text-[#9ca3af] italic">&ldquo;{log.rejection_reason}&rdquo;</div>
                          <div className="mt-2 text-red-400 font-medium flex items-center gap-1">
                            <Sparkles className="w-3 h-3" />
                            <span>Lookalike search executed across peer tech companies</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: Continuous Search Config */}
          {activeTab === 'search_config' && (
            <div className="p-6 md:p-8 rounded-3xl bg-[#0e0e14]/80 border border-white/[0.08] backdrop-blur-2xl space-y-6 max-w-3xl">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2 font-mono">
                  <Sliders className="w-4 h-4 text-red-400" />
                  <span>Continuous Career Search Schedule</span>
                </h3>
                <p className="text-xs text-[#9ca3af] mt-1">
                  Configure scanning frequency across 8 channels, remote preferences, and salary targets.
                </p>
              </div>

              {configMessage && (
                <div className="p-3.5 rounded-2xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs">
                  {configMessage}
                </div>
              )}

              <form onSubmit={handleUpdateSearchConfig} className="space-y-4 text-xs">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[#9ca3af] mb-1.5 font-medium">Search Frequency</label>
                    <select
                      value={searchConfig.search_frequency}
                      onChange={(e) => setSearchConfig({ ...searchConfig, search_frequency: e.target.value })}
                      className="w-full px-3.5 py-2.5 bg-[#08080a] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:border-red-500"
                    >
                      <option value="daily">Daily Continuous Scan</option>
                      <option value="twice_daily">Twice Daily Continuous Scan</option>
                      <option value="weekly">Weekly Summary Scan</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[#9ca3af] mb-1.5 font-medium">Remote Preference</label>
                    <select
                      value={searchConfig.remote_preference}
                      onChange={(e) => setSearchConfig({ ...searchConfig, remote_preference: e.target.value })}
                      className="w-full px-3.5 py-2.5 bg-[#08080a] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:border-red-500"
                    >
                      <option value="remote">Remote Worldwide</option>
                      <option value="hybrid">Hybrid</option>
                      <option value="onsite">On-Site Only</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[#9ca3af] mb-1.5 font-medium">Min Annual Target ($)</label>
                    <input
                      type="number"
                      value={searchConfig.salary_min}
                      onChange={(e) => setSearchConfig({ ...searchConfig, salary_min: Number(e.target.value) })}
                      className="w-full px-3.5 py-2.5 bg-[#08080a] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:border-red-500"
                    />
                  </div>
                  <div>
                    <label className="block text-[#9ca3af] mb-1.5 font-medium">Max Annual Target ($)</label>
                    <input
                      type="number"
                      value={searchConfig.salary_max}
                      onChange={(e) => setSearchConfig({ ...searchConfig, salary_max: Number(e.target.value) })}
                      className="w-full px-3.5 py-2.5 bg-[#08080a] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:border-red-500"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isUpdatingConfig}
                  className="px-6 py-3 bg-gradient-to-r from-red-600 to-rose-600 hover:from-rose-600 hover:to-red-600 text-white font-bold rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-red-600/30"
                >
                  <Check className="w-4 h-4" />
                  <span>{isUpdatingConfig ? 'Saving Configuration…' : 'Save Search Schedule'}</span>
                </button>
              </form>
            </div>
          )}

          {/* TAB 6: Candidate Intelligence Profile */}
          {activeTab === 'profile' && (
            <div className="grid lg:grid-cols-2 gap-6">
              <div className="p-6 rounded-3xl bg-[#0e0e14]/80 border border-white/[0.08] backdrop-blur-2xl space-y-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-red-400 font-mono">
                    <FileUp className="w-4 h-4" />
                    CV Document Ingestion
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded-full border border-white/[0.08] bg-white/[0.03] text-zinc-400 font-mono">
                    PDF • DOCX • TXT
                  </span>
                </div>
                
                <div>
                  <h3 className="text-base font-bold text-white">Upload Your CV or Resume</h3>
                  <p className="text-xs text-[#9ca3af] mt-0.5">
                    EJICODE AI reads your actual CV and extracts factual skills, experience, and contact data with zero hallucination.
                  </p>
                </div>

                {/* File Upload Box */}
                <div className="p-4 rounded-2xl border-2 border-dashed border-white/[0.12] hover:border-red-500/40 transition-colors bg-[#08080a] flex flex-col items-center justify-center gap-2 text-center relative cursor-pointer group">
                  <UploadCloud className="w-8 h-8 text-zinc-400 group-hover:text-red-400 transition-colors" />
                  <span className="text-xs font-semibold text-zinc-200">
                    {isUploadingFile ? 'Ingesting & Analyzing Document…' : 'Click to select CV (PDF, DOCX, TXT)'}
                  </span>
                  <span className="text-[10px] text-zinc-500">Maximum file size 15MB • Zero fabrication verification</span>
                  <input
                    type="file"
                    accept=".pdf,.docx,.doc,.txt"
                    onChange={handleFileUpload}
                    disabled={isUploadingFile}
                    className="absolute inset-0 opacity-0 cursor-pointer disabled:cursor-not-allowed"
                  />
                </div>

                {/* Extracted File Intelligence Card */}
                {uploadedFileInfo && (
                  <div className="p-3.5 bg-black/60 rounded-2xl border border-emerald-500/30 space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-emerald-400 flex items-center gap-1.5 font-mono">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Factual Intelligence Extracted
                      </span>
                      <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 font-mono text-[10px]">
                        {Math.round((uploadedFileInfo.confidence_score || 1) * 100)}% Confidence
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1 pt-1">
                      {uploadedFileInfo.extracted_skills?.slice(0, 8).map((s: string) => (
                        <span key={s} className="px-2 py-0.5 bg-white/[0.04] border border-white/[0.08] rounded text-[11px] text-zinc-200">
                          {s}
                        </span>
                      ))}
                    </div>
                    <div className="text-[11px] text-zinc-400 font-mono pt-1 flex justify-between border-t border-white/[0.05]">
                      <span>Experience: {uploadedFileInfo.experience_years} years</span>
                      <span>Live Opportunities: {uploadedFileInfo.discovered_opportunities_count}</span>
                    </div>
                  </div>
                )}

                {/* Or Paste Raw Text */}
                <div className="pt-2 border-t border-white/[0.06] space-y-2">
                  <div className="flex items-center justify-between text-xs text-zinc-400">
                    <span>Or paste raw text:</span>
                  </div>
                  <textarea
                    rows={3}
                    value={resumeText}
                    onChange={(e) => setResumeText(e.target.value)}
                    placeholder="Paste raw text or Markdown here…"
                    className="w-full px-3.5 py-2 bg-[#08080a] border border-white/[0.08] rounded-xl text-white text-xs focus:outline-none focus:border-red-500 font-mono"
                  />
                  <button
                    onClick={handleParseResume}
                    disabled={isParsingResume || !resumeText.trim()}
                    className="w-full py-2.5 bg-white/[0.04] hover:bg-white/[0.08] disabled:opacity-40 text-zinc-200 font-bold rounded-xl text-xs transition-all flex items-center justify-center gap-2 border border-white/[0.08]"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-red-400" />
                    <span>{isParsingResume ? 'Parsing Factual Signals…' : 'Parse Pasted Text'}</span>
                  </button>
                </div>

                {parseMessage && (
                  <div className="p-3 bg-[#08080a] rounded-xl border border-white/[0.1] text-xs text-zinc-300">
                    {parseMessage}
                  </div>
                )}
              </div>

              <div className="p-6 rounded-3xl bg-[#0e0e14]/80 border border-white/[0.08] backdrop-blur-2xl space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-white">Candidate Parameters</h3>
                  <button
                    onClick={() => setIsEditingProfile(!isEditingProfile)}
                    className="text-xs text-red-400 hover:underline font-semibold"
                  >
                    {isEditingProfile ? 'Cancel' : 'Edit Parameters'}
                  </button>
                </div>

                <form onSubmit={handleUpdateProfile} className="space-y-3 text-xs">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[#9ca3af] mb-1">Full Name</label>
                      <input
                        type="text"
                        disabled={!isEditingProfile}
                        value={editFullName}
                        onChange={(e) => setEditFullName(e.target.value)}
                        placeholder="e.g. Victor Ejike"
                        className="w-full px-3.5 py-2 bg-[#08080a] border border-white/[0.08] rounded-xl text-white disabled:opacity-60"
                      />
                    </div>
                    <div>
                      <label className="block text-[#9ca3af] mb-1">Location</label>
                      <input
                        type="text"
                        disabled={!isEditingProfile}
                        value={editLocation}
                        onChange={(e) => setEditLocation(e.target.value)}
                        placeholder="City, Country"
                        className="w-full px-3.5 py-2 bg-[#08080a] border border-white/[0.08] rounded-xl text-white disabled:opacity-60"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[#9ca3af] mb-1">Headline / Target Role</label>
                    <input
                      type="text"
                      disabled={!isEditingProfile}
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="w-full px-3.5 py-2 bg-[#08080a] border border-white/[0.08] rounded-xl text-white disabled:opacity-60"
                    />
                  </div>

                  <div>
                    <label className="block text-[#9ca3af] mb-1">Skills (Comma-separated)</label>
                    <input
                      type="text"
                      disabled={!isEditingProfile}
                      value={editSkills}
                      onChange={(e) => setEditSkills(e.target.value)}
                      className="w-full px-3.5 py-2 bg-[#08080a] border border-white/[0.08] rounded-xl text-white disabled:opacity-60"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[#9ca3af] mb-1">Min Salary ($)</label>
                      <input
                        type="number"
                        disabled={!isEditingProfile}
                        value={editSalaryMin}
                        onChange={(e) => setEditSalaryMin(e.target.value === '' ? '' : Number(e.target.value))}
                        className="w-full px-3.5 py-2 bg-[#08080a] border border-white/[0.08] rounded-xl text-white disabled:opacity-60"
                      />
                    </div>
                    <div>
                      <label className="block text-[#9ca3af] mb-1">Max Salary ($)</label>
                      <input
                        type="number"
                        disabled={!isEditingProfile}
                        value={editSalaryMax}
                        onChange={(e) => setEditSalaryMax(e.target.value === '' ? '' : Number(e.target.value))}
                        className="w-full px-3.5 py-2 bg-[#08080a] border border-white/[0.08] rounded-xl text-white disabled:opacity-60"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[#9ca3af] mb-1">Career Goal Alignment</label>
                    <textarea
                      rows={2}
                      disabled={!isEditingProfile}
                      value={editGoals}
                      onChange={(e) => setEditGoals(e.target.value)}
                      className="w-full px-3.5 py-2 bg-[#08080a] border border-white/[0.08] rounded-xl text-white disabled:opacity-60"
                    />
                  </div>

                  {isEditingProfile && (
                    <button
                      type="submit"
                      className="w-full py-2.5 bg-gradient-to-r from-red-600 to-rose-600 text-white font-bold rounded-xl text-xs shadow-md shadow-red-600/30"
                    >
                      Save Profile Updates
                    </button>
                  )}
                </form>

                {/* Verified CV Intelligence Cards */}
                {profile && (profile.experience?.length > 0 || profile.education?.length > 0) && (
                  <div className="pt-3 border-t border-white/[0.06] space-y-3">
                    <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider font-semibold">
                      Verified Credentials
                    </div>
                    {profile.experience && profile.experience.length > 0 && (
                      <div className="space-y-1.5">
                        <div className="text-[10px] text-zinc-500 font-mono">Recent Role:</div>
                        <div className="p-2.5 rounded-xl bg-black/40 border border-white/5 text-[11px]">
                          <div className="font-semibold text-white">{profile.experience[0].title}</div>
                          <div className="text-zinc-400">{profile.experience[0].company} {profile.experience[0].start_date ? `(${profile.experience[0].start_date} - ${profile.experience[0].end_date || 'Present'})` : ''}</div>
                        </div>
                      </div>
                    )}
                    {profile.education && profile.education.length > 0 && (
                      <div className="space-y-1.5">
                        <div className="text-[10px] text-zinc-500 font-mono">Education:</div>
                        <div className="p-2.5 rounded-xl bg-black/40 border border-white/5 text-[11px]">
                          <div className="font-semibold text-white">{profile.education[0].degree}</div>
                          <div className="text-zinc-400">{profile.education[0].institution} {profile.education[0].year ? `(${profile.education[0].year})` : ''}</div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* SIDEBAR BENTO MODULES (COL-4) */}
        <div className="lg:col-span-4 space-y-6">
          {/* The live agent stream lives above the tabs - one SSE connection per
              page, not two competing for the same feed. */}

          {/* Bento Widget 2: Proactive Scout Spotlight */}
          <div className="p-6 rounded-3xl apple-glass space-y-3 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-red-600/10 blur-[40px] pointer-events-none rounded-full" />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Flame className="w-4 h-4 text-red-400" />
                <h3 className="text-xs font-mono font-bold text-white uppercase">Client Scout Spotlight</h3>
              </div>
              <span className="text-[10px] text-red-400 font-mono font-bold apple-glass-pill px-2.5 py-0.5">HIGH NEED FIT</span>
            </div>

            <div className="p-4 rounded-2xl apple-glass-subtle space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold text-white">Nova Labs AI</span>
                <span className="text-[10px] font-mono text-emerald-400 apple-glass-pill px-2 py-0.5">95% Fit</span>
              </div>
              <p className="text-[11px] text-zinc-400 leading-relaxed">
                Scaling distributed agent pipelines. Urgent match for your team&apos;s verified Python, FastAPI, and Kubernetes infrastructure.
              </p>
              <div className="pt-2 border-t border-white/10 flex items-center justify-between text-[10px] font-mono">
                <span className="text-zinc-500">Contact: VP Engineering</span>
                <button
                  onClick={() => {
                    setMarketingTargetCompany('Nova Labs AI');
                    setActiveTab('marketing');
                  }}
                  className="text-white hover:text-red-400 font-bold flex items-center gap-1 transition-colors"
                >
                  <span>Pitch</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>

          {/* Bento Widget 3: Continuous Search Engine Status */}
          <div className="p-6 rounded-3xl apple-glass space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-white font-bold flex items-center gap-2">
                <Radio className="w-4 h-4 text-emerald-400" />
                <span>Client Radar Scheduler</span>
              </span>
              <span className="text-emerald-400 font-bold">ACTIVE</span>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between p-2.5 rounded-xl apple-glass-subtle">
                <span className="text-zinc-400">Scan Frequency</span>
                <span className="text-white capitalize">{searchConfig.search_frequency}</span>
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-xl apple-glass-subtle">
                <span className="text-zinc-400">Channel Coverage</span>
                <span className="text-white">8 Channels Live</span>
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-xl apple-glass-subtle">
                <span className="text-zinc-400">Lookalike Recovery</span>
                <span className="text-red-400 font-bold">Automated</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Opportunity Detail & Tailored Outreach Modal */}
      <OpportunityDetailModal
        isOpen={isDetailModalOpen}
        opportunity={selectedOppForModal}
        onClose={() => {
          setIsDetailModalOpen(false);
          setSelectedOppForModal(null);
        }}
        onApplicationDispatched={() => {
          setHiringPipeline((prev) => ({ ...prev, applied: prev.applied + 1 }));
          setApplyMessage('Tailored application outreach dispatched! Multi-channel follow-up cadences scheduled.');
          fetchMatches();
          fetchDashboardData();
        }}
      />
    </div>
  );
}

