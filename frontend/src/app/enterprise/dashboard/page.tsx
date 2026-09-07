'use client';

import { useState, useEffect } from 'react';
import {
  Building2,
  Users,
  Search,
  Sparkles,
  Kanban,
  CheckCircle2,
  Clock,
  ArrowRight,
  TrendingUp,
  UserPlus,
  Trash2,
  ShieldCheck,
  Briefcase,
  ChevronRight,
  Filter,
  ExternalLink,
  PlusCircle,
  X,
  AlertCircle,
  RefreshCw,
  Award,
  Mail,
  Phone,
  Github,
  Linkedin,
} from 'lucide-react';

interface Candidate {
  id: string;
  full_name: string;
  email?: string;
  phone?: string;
  title: string;
  skills: string[];
  experience_summary?: string;
  location?: string;
  github_url?: string;
  linkedin_url?: string;
  portfolio_url?: string;
  status: 'discovered' | 'screening' | 'interviewing' | 'offered' | 'hired' | 'rejected';
  match_score: number;
  match_explanation?: string;
  source?: string;
  notes?: string;
  created_at?: string;
}

interface TeamMember {
  id: string;
  user_id: string;
  full_name: string;
  email: string;
  role: 'owner' | 'admin' | 'recruiter' | 'member';
  permissions: string[];
  joined_at?: string;
}

interface OrgStats {
  organization_name: string;
  plan_tier: string;
  total_candidates: number;
  stage_distribution: Record<string, number>;
  team_members_count: number;
  average_match_score: number;
  screening_to_interview_rate: number;
  interview_to_offer_rate: number;
}

const STAGES = [
  { key: 'discovered', label: 'Discovered', color: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' },
  { key: 'screening', label: 'Screening', color: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  { key: 'interviewing', label: 'Interviewing', color: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
  { key: 'offered', label: 'Offered', color: 'bg-purple-500/10 text-purple-400 border-purple-500/20' },
  { key: 'hired', label: 'Hired', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
];

export default function EnterpriseDashboard() {
  const [token, setToken] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'pipeline' | 'scout' | 'team' | 'analytics'>('pipeline');

  // Stats
  const [stats, setStats] = useState<OrgStats>({
    organization_name: 'Acme Enterprise',
    plan_tier: 'enterprise_scale',
    total_candidates: 12,
    stage_distribution: {
      discovered: 5,
      screening: 3,
      interviewing: 2,
      offered: 1,
      hired: 1,
      rejected: 0,
    },
    team_members_count: 4,
    average_match_score: 89.2,
    screening_to_interview_rate: 66.7,
    interview_to_offer_rate: 50.0,
  });

  // Candidates & Kanban
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [isLoadingCandidates, setIsLoadingCandidates] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [candidateNotes, setCandidateNotes] = useState('');
  const [isUpdatingStage, setIsUpdatingStage] = useState(false);

  // AI Scout Form
  const [scoutRoleTitle, setScoutRoleTitle] = useState('Senior Distributed Systems Engineer');
  const [scoutSkills, setScoutSkills] = useState('Python, Go, Kubernetes, Redis, Distributed Systems');
  const [scoutLocation, setScoutLocation] = useState('Remote');
  const [isScouting, setIsScouting] = useState(false);
  const [scoutMessage, setScoutMessage] = useState<string | null>(null);

  // Manual Add Candidate Form
  const [showAddModal, setShowAddModal] = useState(false);
  const [newCandName, setNewCandName] = useState('');
  const [newCandEmail, setNewCandEmail] = useState('');
  const [newCandTitle, setNewCandTitle] = useState('');
  const [newCandSkills, setNewCandSkills] = useState('');
  const [newCandLocation, setNewCandLocation] = useState('Remote');
  const [newCandNotes, setNewCandNotes] = useState('');
  const [isAddingCandidate, setIsAddingCandidate] = useState(false);

  // Team
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [isLoadingTeam, setIsLoadingTeam] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteName, setInviteName] = useState('');
  const [inviteRole, setInviteRole] = useState<'admin' | 'recruiter' | 'member'>('recruiter');
  const [isInviting, setIsInviting] = useState(false);
  const [teamMessage, setTeamMessage] = useState<string | null>(null);

  useEffect(() => {
    const t = localStorage.getItem('token');
    setToken(t);
  }, []);

  const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

  const fetchDashboardData = async () => {
    if (!token) return;
    try {
      // 1. Fetch Stats
      const statsRes = await fetch('http://localhost:8000/v1/enterprise/dashboard-stats', {
        headers: authHeaders,
      });
      if (statsRes.ok) {
        const d = await statsRes.json();
        if (d.data) setStats(d.data);
      }

      // 2. Fetch Candidates
      setIsLoadingCandidates(true);
      const candRes = await fetch('http://localhost:8000/v1/enterprise/candidates', {
        headers: authHeaders,
      });
      if (candRes.ok) {
        const d = await candRes.json();
        if (d.candidates) setCandidates(d.candidates);
      }
      setIsLoadingCandidates(false);

      // 3. Fetch Team
      setIsLoadingTeam(true);
      const teamRes = await fetch('http://localhost:8000/v1/enterprise/team', {
        headers: authHeaders,
      });
      if (teamRes.ok) {
        const d = await teamRes.json();
        if (d.team) setTeam(d.team);
      }
      setIsLoadingTeam(false);
    } catch (e) {
      console.warn('Backend not responding, displaying loaded telemetry:', e);
      setIsLoadingCandidates(false);
      setIsLoadingTeam(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchDashboardData();
    }
  }, [token]);

  // Stage advancement
  const handleUpdateStage = async (candidateId: string, nextStage: string, notes?: string) => {
    setIsUpdatingStage(true);
    try {
      const res = await fetch(`http://localhost:8000/v1/enterprise/candidates/${candidateId}/stage`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify({ stage: nextStage, notes }),
      });

      if (res.ok) {
        setCandidates((prev) =>
          prev.map((c) => (c.id === candidateId ? { ...c, status: nextStage as any } : c))
        );
        if (selectedCandidate && selectedCandidate.id === candidateId) {
          setSelectedCandidate({ ...selectedCandidate, status: nextStage as any });
        }
        fetchDashboardData();
      }
    } catch (e) {
      console.error('Failed to advance stage:', e);
    } finally {
      setIsUpdatingStage(false);
    }
  };

  // Run AI Scout
  const handleRunScout = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsScouting(true);
    setScoutMessage(null);

    const skillsArray = scoutSkills.split(',').map((s) => s.trim()).filter(Boolean);

    try {
      const res = await fetch('http://localhost:8000/v1/enterprise/search-candidates', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify({
          role_title: scoutRoleTitle,
          required_skills: skillsArray,
          min_experience_years: 4.0,
          location: scoutLocation,
        }),
      });

      const data = await res.json();
      if (res.ok && data.candidates) {
        setScoutMessage(`AI Agent scouted and aligned ${data.candidates.length} verified candidate profiles!`);
        fetchDashboardData();
        setActiveTab('pipeline');
      } else {
        setScoutMessage(data.detail || 'Scouting completed.');
      }
    } catch (err: any) {
      setScoutMessage('Scout simulation queued. Check connection to API backend.');
    } finally {
      setIsScouting(false);
    }
  };

  // Add Manual Candidate
  const handleAddCandidate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsAddingCandidate(true);
    const skillsArray = newCandSkills.split(',').map((s) => s.trim()).filter(Boolean);

    try {
      const res = await fetch('http://localhost:8000/v1/enterprise/candidates', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify({
          full_name: newCandName,
          email: newCandEmail || undefined,
          title: newCandTitle,
          skills: skillsArray,
          location: newCandLocation,
          notes: newCandNotes,
        }),
      });

      if (res.ok) {
        setShowAddModal(false);
        setNewCandName('');
        setNewCandEmail('');
        setNewCandTitle('');
        setNewCandSkills('');
        setNewCandNotes('');
        fetchDashboardData();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsAddingCandidate(false);
    }
  };

  // Invite Team Member
  const handleInviteTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsInviting(true);
    setTeamMessage(null);

    try {
      const res = await fetch('http://localhost:8000/v1/enterprise/team', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify({
          full_name: inviteName,
          email: inviteEmail,
          role: inviteRole,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setTeamMessage(`Successfully invited ${inviteEmail} as ${inviteRole}.`);
        setInviteName('');
        setInviteEmail('');
        fetchDashboardData();
      } else {
        setTeamMessage(data.detail || 'Failed to invite team member.');
      }
    } catch (e: any) {
      setTeamMessage('Error connecting to backend team service.');
    } finally {
      setIsInviting(false);
    }
  };

  // Remove Team Member
  const handleRemoveTeam = async (userId: string) => {
    if (!confirm('Are you sure you want to remove this team member?')) return;
    try {
      const res = await fetch(`http://localhost:8000/v1/enterprise/team/${userId}`, {
        method: 'DELETE',
        headers: authHeaders,
      });
      if (res.ok) {
        setTeam((prev) => prev.filter((m) => m.user_id !== userId));
        fetchDashboardData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8">
      {/* Header Banner */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-600/10 border border-blue-500/20 rounded-xl">
              <Building2 className="w-8 h-8 text-blue-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-white tracking-tight">{stats.organization_name}</h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase tracking-wider">
                  {stats.plan_tier.replace('_', ' ')}
                </span>
              </div>
              <p className="text-sm text-slate-400 mt-0.5">
                Autonomous Talent Pipeline, AI Multi-Track Sourcing & Team RBAC
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-sm font-medium transition"
            >
              <PlusCircle className="w-4 h-4 text-slate-300" />
              Add Candidate
            </button>
            <button
              onClick={() => setActiveTab('scout')}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-sm font-semibold shadow-lg shadow-blue-500/20 transition"
            >
              <Sparkles className="w-4 h-4" />
              AI Talent Scout
            </button>
          </div>
        </div>

        {/* Real-time Telemetry Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Pipeline Candidates</span>
              <Users className="w-4 h-4 text-blue-400" />
            </div>
            <div className="text-2xl font-bold text-white mt-2">{stats.total_candidates}</div>
            <div className="text-xs text-slate-500 mt-1">Across all Kanban stages</div>
          </div>

          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Avg Match Score</span>
              <Award className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-emerald-400 mt-2">{stats.average_match_score}%</div>
            <div className="text-xs text-slate-500 mt-1">Weighted 6-factor rubric</div>
          </div>

          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Screening → Interview</span>
              <TrendingUp className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="text-2xl font-bold text-white mt-2">{stats.screening_to_interview_rate}%</div>
            <div className="text-xs text-slate-500 mt-1">Conversion velocity</div>
          </div>

          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Team Members</span>
              <ShieldCheck className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-2xl font-bold text-white mt-2">{stats.team_members_count}</div>
            <div className="text-xs text-slate-500 mt-1">RBAC authenticated</div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-800 mt-8 pb-3">
          <button
            onClick={() => setActiveTab('pipeline')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === 'pipeline'
                ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Kanban className="w-4 h-4" />
            Pipeline Kanban
          </button>
          <button
            onClick={() => setActiveTab('scout')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === 'scout'
                ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            Autonomous Scout
          </button>
          <button
            onClick={() => setActiveTab('team')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === 'team'
                ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Users className="w-4 h-4" />
            Team & RBAC
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="max-w-7xl mx-auto">
        {/* TAB 1: KANBAN PIPELINE */}
        {activeTab === 'pipeline' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-white">Talent Pipeline Kanban</h2>
                <p className="text-sm text-slate-400">
                  Track, evaluate, and advance candidates seamlessly through stages.
                </p>
              </div>
              <button
                onClick={fetchDashboardData}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 text-xs text-slate-300 transition"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingCandidates ? 'animate-spin' : ''}`} />
                Refresh Board
              </button>
            </div>

            {/* Kanban Columns */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              {STAGES.map((stage) => {
                const stageCandidates = candidates.filter((c) => c.status === stage.key);
                return (
                  <div
                    key={stage.key}
                    className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 flex flex-col min-h-[600px]"
                  >
                    <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded-md text-xs font-semibold border ${stage.color}`}>
                          {stage.label}
                        </span>
                      </div>
                      <span className="text-xs font-mono text-slate-400 bg-slate-800/60 px-2 py-0.5 rounded-full">
                        {stageCandidates.length}
                      </span>
                    </div>

                    <div className="space-y-3 flex-1 overflow-y-auto pr-1">
                      {stageCandidates.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-48 border border-dashed border-slate-800/60 rounded-xl text-slate-500 text-xs text-center p-4">
                          <span>No candidates</span>
                        </div>
                      ) : (
                        stageCandidates.map((c) => (
                          <div
                            key={c.id}
                            onClick={() => setSelectedCandidate(c)}
                            className="bg-slate-900/90 hover:bg-slate-850 border border-slate-800 hover:border-slate-700 rounded-xl p-3.5 cursor-pointer transition shadow-sm hover:shadow-md"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <h4 className="font-semibold text-white text-sm">{c.full_name}</h4>
                                <p className="text-xs text-slate-400 line-clamp-1">{c.title}</p>
                              </div>
                              <span
                                className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                                  c.match_score >= 85
                                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                    : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                }`}
                              >
                                {c.match_score}%
                              </span>
                            </div>

                            {/* Skills snippet */}
                            <div className="flex flex-wrap gap-1 mt-2.5">
                              {(c.skills || []).slice(0, 3).map((s, idx) => (
                                <span
                                  key={idx}
                                  className="text-[10px] px-1.5 py-0.5 bg-slate-800 text-slate-300 rounded"
                                >
                                  {s}
                                </span>
                              ))}
                              {(c.skills || []).length > 3 && (
                                <span className="text-[10px] text-slate-500">
                                  +{(c.skills || []).length - 3}
                                </span>
                              )}
                            </div>

                            {/* Actions / Stage Steppers */}
                            <div className="flex items-center justify-between pt-3 mt-3 border-t border-slate-800/60 text-[11px] text-slate-400">
                              <span>{c.location || 'Remote'}</span>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  const curIdx = STAGES.findIndex((st) => st.key === stage.key);
                                  if (curIdx < STAGES.length - 1) {
                                    handleUpdateStage(c.id, STAGES[curIdx + 1].key);
                                  }
                                }}
                                className="flex items-center gap-1 text-blue-400 hover:text-blue-300 font-medium"
                              >
                                Advance
                                <ChevronRight className="w-3 h-3" />
                              </button>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* TAB 2: AI TALENT SCOUT */}
        {activeTab === 'scout' && (
          <div className="max-w-3xl mx-auto bg-slate-900/60 border border-slate-800 rounded-2xl p-8 backdrop-blur-xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-3 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl shadow-lg shadow-blue-500/20">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-white">Autonomous Talent Scout</h3>
                <p className="text-sm text-slate-400">
                  Deploy autonomous agents across GitHub, LinkedIn, and developer networks to discover and score top engineers.
                </p>
              </div>
            </div>

            {scoutMessage && (
              <div className="mb-6 p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-300 text-sm flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-blue-400 shrink-0" />
                <span>{scoutMessage}</span>
              </div>
            )}

            <form onSubmit={handleRunScout} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Target Role Title
                </label>
                <input
                  type="text"
                  required
                  value={scoutRoleTitle}
                  onChange={(e) => setScoutRoleTitle(e.target.value)}
                  placeholder="e.g. Lead Distributed Systems Engineer"
                  className="w-full px-4 py-3 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Required Core Skills (comma-separated)
                </label>
                <input
                  type="text"
                  required
                  value={scoutSkills}
                  onChange={(e) => setScoutSkills(e.target.value)}
                  placeholder="e.g. Go, Kubernetes, Rust, gRPC, Kafka"
                  className="w-full px-4 py-3 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Location Preference
                </label>
                <input
                  type="text"
                  value={scoutLocation}
                  onChange={(e) => setScoutLocation(e.target.value)}
                  placeholder="e.g. Remote, San Francisco, London"
                  className="w-full px-4 py-3 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 text-sm"
                />
              </div>

              <div className="pt-4 border-t border-slate-800">
                <button
                  type="submit"
                  disabled={isScouting}
                  className="w-full flex items-center justify-center gap-2 py-3.5 px-6 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold shadow-lg shadow-blue-500/25 transition disabled:opacity-50"
                >
                  {isScouting ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      Dispatching Autonomous Agent Scout...
                    </>
                  ) : (
                    <>
                      <Search className="w-5 h-5" />
                      Scout & Align Verified Candidates
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* TAB 3: TEAM & RBAC */}
        {activeTab === 'team' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Invite Form */}
            <div className="md:col-span-1 bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl h-fit">
              <h3 className="text-base font-bold text-white mb-1">Invite Team Member</h3>
              <p className="text-xs text-slate-400 mb-5">
                Collaborate with hiring managers and recruiters under multi-tenant isolation.
              </p>

              {teamMessage && (
                <div className="mb-4 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs">
                  {teamMessage}
                </div>
              )}

              <form onSubmit={handleInviteTeam} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">Full Name</label>
                  <input
                    type="text"
                    required
                    value={inviteName}
                    onChange={(e) => setInviteName(e.target.value)}
                    placeholder="Jane Doe"
                    className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">Work Email</label>
                  <input
                    type="email"
                    required
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="jane@company.com"
                    className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">Role Permission</label>
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value as any)}
                    className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-blue-500"
                  >
                    <option value="recruiter">Recruiter (Search, Screen, Move Candidates)</option>
                    <option value="admin">Admin (Full Team & Org Access)</option>
                    <option value="member">Member (Read Only)</option>
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={isInviting}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition disabled:opacity-50"
                >
                  <UserPlus className="w-4 h-4" />
                  {isInviting ? 'Inviting...' : 'Send Invitation'}
                </button>
              </form>
            </div>

            {/* Team Members List */}
            <div className="md:col-span-2 bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-base font-bold text-white">Active Organization Members</h3>
                  <p className="text-xs text-slate-400">Members with access to this tenant workspace.</p>
                </div>
                <span className="text-xs font-mono bg-slate-800 px-2.5 py-1 rounded-full text-slate-300">
                  {team.length} Users
                </span>
              </div>

              <div className="divide-y divide-slate-800/80">
                {team.map((member) => (
                  <div key={member.id} className="py-4 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center font-bold text-slate-300 text-sm">
                        {member.full_name ? member.full_name[0].toUpperCase() : 'U'}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold text-white text-sm">{member.full_name}</h4>
                          <span
                            className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${
                              member.role === 'owner'
                                ? 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                                : member.role === 'admin'
                                ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                                : 'bg-slate-800 text-slate-300 border-slate-700'
                            }`}
                          >
                            {member.role}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400">{member.email}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {member.role !== 'owner' && (
                        <button
                          onClick={() => handleRemoveTeam(member.user_id)}
                          className="p-1.5 text-slate-500 hover:text-red-400 transition"
                          title="Remove from organization"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Candidate Detail Modal */}
      {selectedCandidate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 shadow-2xl">
            <div className="flex items-start justify-between pb-4 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-3">
                  <h3 className="text-xl font-bold text-white">{selectedCandidate.full_name}</h3>
                  <span className="px-2 py-0.5 rounded-md text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {selectedCandidate.match_score}% Match
                  </span>
                </div>
                <p className="text-sm text-slate-400 mt-1">{selectedCandidate.title}</p>
              </div>
              <button
                onClick={() => setSelectedCandidate(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="py-5 space-y-5">
              {/* Natural Language Alignment */}
              <div className="p-4 rounded-xl bg-blue-500/5 border border-blue-500/15">
                <div className="flex items-center gap-2 text-xs font-semibold text-blue-400 uppercase tracking-wider mb-1.5">
                  <Sparkles className="w-3.5 h-3.5" />
                  AI Alignment Rationale
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {selectedCandidate.match_explanation || 'Candidate satisfies primary technical competencies and domain experience.'}
                </p>
              </div>

              {/* Skills */}
              <div>
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Verified Skills</h4>
                <div className="flex flex-wrap gap-1.5">
                  {(selectedCandidate.skills || []).map((skill, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-md text-xs bg-slate-800 text-slate-200 border border-slate-700/60"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              {/* Experience Summary */}
              {selectedCandidate.experience_summary && (
                <div>
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Experience</h4>
                  <p className="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3 rounded-lg border border-slate-800">
                    {selectedCandidate.experience_summary}
                  </p>
                </div>
              )}

              {/* Contact / Links */}
              <div className="flex flex-wrap gap-4 pt-2">
                {selectedCandidate.email && (
                  <a
                    href={`mailto:${selectedCandidate.email}`}
                    className="flex items-center gap-1.5 text-xs text-slate-300 hover:text-blue-400 transition"
                  >
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    {selectedCandidate.email}
                  </a>
                )}
                {selectedCandidate.github_url && (
                  <a
                    href={selectedCandidate.github_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 text-xs text-slate-300 hover:text-blue-400 transition"
                  >
                    <Github className="w-3.5 h-3.5 text-slate-400" />
                    GitHub
                  </a>
                )}
                {selectedCandidate.linkedin_url && (
                  <a
                    href={selectedCandidate.linkedin_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 text-xs text-slate-300 hover:text-blue-400 transition"
                  >
                    <Linkedin className="w-3.5 h-3.5 text-slate-400" />
                    LinkedIn
                  </a>
                )}
              </div>

              {/* Stage Transition Selector */}
              <div className="pt-4 border-t border-slate-800">
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Change Pipeline Stage
                </label>
                <div className="grid grid-cols-5 gap-2">
                  {STAGES.map((st) => (
                    <button
                      key={st.key}
                      onClick={() => handleUpdateStage(selectedCandidate.id, st.key)}
                      className={`px-3 py-2 rounded-lg text-xs font-medium border text-center transition ${
                        selectedCandidate.status === st.key
                          ? `${st.color} font-bold ring-2 ring-blue-500/20`
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      {st.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Manual Candidate Creation Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-5">
              <h3 className="text-lg font-bold text-white">Add Candidate to Pipeline</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddCandidate} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={newCandName}
                  onChange={(e) => setNewCandName(e.target.value)}
                  placeholder="Alex Mercer"
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Email</label>
                <input
                  type="email"
                  value={newCandEmail}
                  onChange={(e) => setNewCandEmail(e.target.value)}
                  placeholder="alex.mercer@dev.io"
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Job Title</label>
                <input
                  type="text"
                  required
                  value={newCandTitle}
                  onChange={(e) => setNewCandTitle(e.target.value)}
                  placeholder="Senior Backend Engineer"
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Skills (comma-separated)</label>
                <input
                  type="text"
                  required
                  value={newCandSkills}
                  onChange={(e) => setNewCandSkills(e.target.value)}
                  placeholder="Python, FastAPI, Postgres, Docker"
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isAddingCandidate}
                  className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition disabled:opacity-50"
                >
                  {isAddingCandidate ? 'Adding...' : 'Add Candidate'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
