'use client';

import { useState, useEffect } from 'react';
import useSWR from 'swr';
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
  Sliders,
} from 'lucide-react';

export default function IndividualDashboard() {
  const [token, setToken] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'matches' | 'profile' | 'rejection'>('matches');

  // Stats
  const [stats, setStats] = useState({
    profile_completion_percentage: 65,
    active_matches: 14,
    applications_sent: 4,
    scheduled_follow_ups: 3,
    rejections_recovered: 2,
    average_match_score: 86.4,
    candidate_title: 'Software Engineer',
    candidate_name: 'Candidate',
  });

  // Profile data
  const [profile, setProfile] = useState<any>(null);
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editBio, setEditBio] = useState('');
  const [editSkills, setEditSkills] = useState('');
  const [editSalaryMin, setEditSalaryMin] = useState<number>(100000);
  const [editSalaryMax, setEditSalaryMax] = useState<number>(160000);
  const [editGoals, setEditGoals] = useState('');

  // Resume parse
  const [resumeText, setResumeText] = useState('');
  const [isParsingResume, setIsParsingResume] = useState(false);
  const [parseMessage, setParseMessage] = useState<string | null>(null);

  // Opportunities
  const [matches, setMatches] = useState<any[]>([]);
  const [isLoadingMatches, setIsLoadingMatches] = useState(false);
  const [isMatching, setIsMatching] = useState(false);
  const [applyMessage, setApplyMessage] = useState<string | null>(null);

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

  // Fetch stats and profile
  const fetchDashboardData = async () => {
    if (!token) return;
    try {
      const statsRes = await fetch('http://localhost:8000/v1/individual/dashboard-stats', {
        headers: authHeaders,
      });
      if (statsRes.ok) {
        const d = await statsRes.json();
        if (d.data) setStats(d.data);
      }

      const profRes = await fetch('http://localhost:8000/v1/individual/profile', {
        headers: authHeaders,
      });
      if (profRes.ok) {
        const d = await profRes.json();
        if (d.profile) {
          setProfile(d.profile);
          setEditTitle(d.profile.title || '');
          setEditBio(d.profile.bio || '');
          setEditSkills((d.profile.skills || []).join(', '));
          setEditSalaryMin(d.profile.salary_min || 100000);
          setEditSalaryMax(d.profile.salary_max || 160000);
          setEditGoals(d.profile.career_goals || '');
        }
      }

      // Fetch matches
      fetchMatches();

      // Fetch rejections
      const rejRes = await fetch('http://localhost:8000/v1/individual/rejections', {
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
      const res = await fetch('http://localhost:8000/v1/individual/matches?min_score=50', {
        headers: authHeaders,
      });
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

  useEffect(() => {
    if (token) {
      fetchDashboardData();
    }
  }, [token]);

  // Handle Search & Match trigger
  const handleTriggerSearch = async () => {
    setIsMatching(true);
    setApplyMessage(null);
    try {
      const res = await fetch('http://localhost:8000/v1/individual/search', {
        method: 'POST',
        headers: authHeaders,
      });
      if (res.ok) {
        await fetchMatches();
        await fetchDashboardData();
        setApplyMessage('AI discovery & 6-factor alignment scoring refreshed successfully!');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsMatching(false);
    }
  };

  // Handle Apply
  const handleApply = async (oppId: string, title: string) => {
    try {
      const res = await fetch('http://localhost:8000/v1/individual/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({
          opportunity_id: oppId,
          custom_note: `High alignment application for ${title}.`,
        }),
      });
      const d = await res.json();
      if (res.ok) {
        setApplyMessage(`Application outreach dispatched! Day 3, 7, and 14 follow-ups scheduled.`);
        fetchDashboardData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Handle Resume Parse
  const handleParseResume = async () => {
    if (!resumeText.trim()) return;
    setIsParsingResume(true);
    setParseMessage(null);
    try {
      const res = await fetch('http://localhost:8000/v1/individual/profile/resume-parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ resume_text: resumeText }),
      });
      const d = await res.json();
      if (res.ok) {
        setParseMessage(`Parsed ${d.extracted_skills?.length || 0} skills: ${d.extracted_skills?.join(', ')}`);
        fetchDashboardData();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsParsingResume(false);
    }
  };

  // Handle Profile Update
  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const skillsArray = editSkills.split(',').map((s) => s.trim()).filter(Boolean);
      const res = await fetch('http://localhost:8000/v1/individual/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({
          title: editTitle,
          bio: editBio,
          skills: skillsArray,
          salary_min: Number(editSalaryMin),
          salary_max: Number(editSalaryMax),
          career_goals: editGoals,
        }),
      });
      if (res.ok) {
        setIsEditingProfile(false);
        fetchDashboardData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Handle Rejection Recovery
  const handleRejectionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectionOppId || !rejectionReason.trim()) return;
    setIsProcessingRejection(true);
    try {
      const res = await fetch('http://localhost:8000/v1/individual/rejections', {
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
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Welcome Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-[#161b22] to-[#0d1117] border border-[#30363d] flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-xl">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#58a6ff]">
            <Sparkles className="w-3.5 h-3.5" />
            Candidate Career Acceleration
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white mt-1">
            Welcome, {stats.candidate_name}
          </h1>
          <p className="text-sm text-[#8b949e] mt-1">
            Target Role: <span className="text-white font-medium">{stats.candidate_title}</span> • 6-Factor Alignment Engine Active
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleTriggerSearch}
            disabled={isMatching}
            className="px-5 py-2.5 bg-[#1f6feb] hover:bg-[#388bfd] disabled:opacity-50 text-white font-semibold rounded-xl text-sm transition-all shadow-md shadow-[#1f6feb]/20 flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isMatching ? 'animate-spin' : ''}`} />
            <span>{isMatching ? 'Evaluating Matches…' : 'Run Alignment Matching'}</span>
          </button>
        </div>
      </div>

      {applyMessage && (
        <div className="p-4 rounded-xl bg-emerald-900/30 border border-emerald-700/50 flex items-center gap-3 text-emerald-200 text-sm">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <div>{applyMessage}</div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Profile Completion */}
        <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d]">
          <div className="text-xs text-[#8b949e] font-medium">Profile Completion</div>
          <div className="text-2xl font-bold text-white mt-2">
            {stats.profile_completion_percentage}%
          </div>
          <div className="w-full bg-[#21262d] h-1.5 rounded-full mt-2 overflow-hidden">
            <div
              className="bg-[#2ea043] h-full rounded-full"
              style={{ width: `${stats.profile_completion_percentage}%` }}
            ></div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d]">
          <div className="text-xs text-[#8b949e] font-medium">Ranked Matches</div>
          <div className="text-2xl font-bold text-white mt-2">{stats.active_matches}</div>
          <div className="text-[11px] text-[#58a6ff] mt-1 font-medium">&gt;60% alignment</div>
        </div>

        <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d]">
          <div className="text-xs text-[#8b949e] font-medium">Applications Sent</div>
          <div className="text-2xl font-bold text-white mt-2">{stats.applications_sent}</div>
          <div className="text-[11px] text-[#2ea043] mt-1 font-medium">Direct Outreach</div>
        </div>

        <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d]">
          <div className="text-xs text-[#8b949e] font-medium">Scheduled Touches</div>
          <div className="text-2xl font-bold text-white mt-2">{stats.scheduled_follow_ups}</div>
          <div className="text-[11px] text-[#a371f7] mt-1 font-medium">Day 3 / 7 / 14</div>
        </div>

        <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d]">
          <div className="text-xs text-[#8b949e] font-medium">Rejections Recovered</div>
          <div className="text-2xl font-bold text-white mt-2">{stats.rejections_recovered}</div>
          <div className="text-[11px] text-[#d29922] mt-1 font-medium">Lookalikes Queued</div>
        </div>

        <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d]">
          <div className="text-xs text-[#8b949e] font-medium">Average Alignment</div>
          <div className="text-2xl font-bold text-white mt-2">{stats.average_match_score}%</div>
          <div className="text-[11px] text-[#58a6ff] mt-1 font-medium">6-Factor Rubric</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#30363d] gap-6 text-sm">
        <button
          onClick={() => setActiveTab('matches')}
          className={`pb-3 font-semibold transition-colors border-b-2 ${
            activeTab === 'matches'
              ? 'text-white border-[#1f6feb]'
              : 'text-[#8b949e] border-transparent hover:text-white'
          }`}
        >
          Matched Opportunities ({matches.length})
        </button>
        <button
          onClick={() => setActiveTab('rejection')}
          className={`pb-3 font-semibold transition-colors border-b-2 ${
            activeTab === 'rejection'
              ? 'text-white border-[#1f6feb]'
              : 'text-[#8b949e] border-transparent hover:text-white'
          }`}
        >
          Rejection Recovery Engine
        </button>
        <button
          onClick={() => setActiveTab('profile')}
          className={`pb-3 font-semibold transition-colors border-b-2 ${
            activeTab === 'profile'
              ? 'text-white border-[#1f6feb]'
              : 'text-[#8b949e] border-transparent hover:text-white'
          }`}
        >
          Profile & Resume Parser
        </button>
      </div>

      {/* TAB 1: Matched Opportunities */}
      {activeTab === 'matches' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white">Top Ranked Roles</h2>
            <div className="text-xs text-[#8b949e]">
              Scored on Skills (35%), Experience (20%), Location (10%), Comp (10%), Tech (10%), Goals (15%)
            </div>
          </div>

          {isLoadingMatches ? (
            <div className="p-12 text-center text-[#8b949e] animate-pulse">Loading verified opportunities…</div>
          ) : matches.length === 0 ? (
            <div className="p-8 rounded-xl bg-[#161b22] border border-[#30363d] text-center">
              <Compass className="w-8 h-8 text-[#8b949e] mx-auto mb-3" />
              <div className="text-white font-medium">No matches evaluated yet</div>
              <p className="text-xs text-[#8b949e] mt-1">Click &quot;Run Alignment Matching&quot; above to score current opportunities against your profile.</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {matches.map((opp) => (
                <div
                  key={opp.id}
                  className="p-5 rounded-xl bg-[#161b22] border border-[#30363d] hover:border-[#388bfd]/50 transition-all"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2.5">
                        <span className="text-lg font-bold text-white">{opp.title}</span>
                        <span className="px-2 py-0.5 text-xs font-mono font-bold rounded bg-[#1f6feb]/20 text-[#58a6ff] border border-[#1f6feb]/40">
                          {opp.score}% Match
                        </span>
                        <span className="px-2 py-0.5 text-xs rounded bg-[#21262d] text-[#8b949e]">
                          {opp.location_type || 'remote'}
                        </span>
                      </div>
                      <div className="text-xs text-[#8b949e] mt-1 flex items-center gap-3">
                        <span>{opp.company_name}</span>
                        <span>•</span>
                        <span>{opp.company_industry}</span>
                        <span>•</span>
                        <span>
                          {opp.salary_min && opp.salary_max
                            ? `$${(opp.salary_min / 1000).toFixed(0)}k - $${(opp.salary_max / 1000).toFixed(0)}k`
                            : 'Competitive'}
                        </span>
                        <span>•</span>
                        <span className="text-[#a371f7]">Source: {opp.source_platform}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleApply(opp.id, opp.title)}
                        className="px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-colors shadow-sm"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>Apply &amp; Cadence</span>
                      </button>
                    </div>
                  </div>

                  {/* 6-Factor Score Pills */}
                  {opp.score_breakdown && (
                    <div className="mt-4 pt-3 border-t border-[#30363d] flex flex-wrap gap-2 text-[11px]">
                      <span className="bg-[#0d1117] px-2.5 py-1 rounded-md text-[#c9d1d9] border border-[#30363d]">
                        Skills: <strong className="text-[#58a6ff]">{opp.score_breakdown.skills_match || 0}/35</strong>
                      </span>
                      <span className="bg-[#0d1117] px-2.5 py-1 rounded-md text-[#c9d1d9] border border-[#30363d]">
                        Experience: <strong className="text-[#58a6ff]">{opp.score_breakdown.experience_match || 0}/20</strong>
                      </span>
                      <span className="bg-[#0d1117] px-2.5 py-1 rounded-md text-[#c9d1d9] border border-[#30363d]">
                        Location: <strong className="text-[#58a6ff]">{opp.score_breakdown.location_match || 0}/10</strong>
                      </span>
                      <span className="bg-[#0d1117] px-2.5 py-1 rounded-md text-[#c9d1d9] border border-[#30363d]">
                        Salary: <strong className="text-[#58a6ff]">{opp.score_breakdown.salary_match || 0}/10</strong>
                      </span>
                      <span className="bg-[#0d1117] px-2.5 py-1 rounded-md text-[#c9d1d9] border border-[#30363d]">
                        Tech Stack: <strong className="text-[#58a6ff]">{opp.score_breakdown.technology_match || 0}/10</strong>
                      </span>
                      <span className="bg-[#0d1117] px-2.5 py-1 rounded-md text-[#c9d1d9] border border-[#30363d]">
                        Goals: <strong className="text-[#58a6ff]">{opp.score_breakdown.career_goal_match || 0}/15</strong>
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Rejection Recovery Engine */}
      {activeTab === 'rejection' && (
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="p-6 rounded-xl bg-[#161b22] border border-[#30363d] space-y-4">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#d29922]">
                <RefreshCw className="w-3.5 h-3.5" />
                Continuous Opportunity Flow
              </div>
              <h3 className="text-lg font-bold text-white mt-1">Log Rejection to Recover Lookalikes</h3>
              <p className="text-xs text-[#8b949e] mt-1">
                Rejection must never end the workflow. When an opportunity passes, the agent categorizes feedback, discovers peer lookalike companies, and extracts alternate hiring contacts.
              </p>
            </div>

            <form onSubmit={handleRejectionSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                  Select Opportunity
                </label>
                <select
                  value={rejectionOppId}
                  onChange={(e) => setRejectionOppId(e.target.value)}
                  className="w-full px-3 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-xs focus:outline-none focus:border-[#1f6feb]"
                >
                  {matches.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.title} at {m.company_name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                  Feedback or Rejection Message
                </label>
                <textarea
                  rows={3}
                  required
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="e.g. Role was filled internally, but your distributed systems experience with FastAPI and PostgreSQL was impressive."
                  className="w-full px-3 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-xs focus:outline-none focus:border-[#1f6feb]"
                />
              </div>

              <button
                type="submit"
                disabled={isProcessingRejection || !rejectionReason.trim()}
                className="w-full py-2.5 bg-[#d29922] hover:bg-[#e3b341] text-black font-bold rounded-xl text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isProcessingRejection ? 'animate-spin' : ''}`} />
                <span>{isProcessingRejection ? 'Analyzing & Discovering…' : 'Activate Lookalike Recovery'}</span>
              </button>
            </form>
          </div>

          {/* Recovery Output & History */}
          <div className="space-y-4">
            {recoveryOutput && (
              <div className="p-5 rounded-xl bg-[#0d1117] border border-[#238636] space-y-3">
                <div className="flex items-center gap-2 text-[#2ea043] font-bold text-sm">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Recovery Package Activated</span>
                </div>
                <p className="text-xs text-[#c9d1d9]">{recoveryOutput.recovery_strategy}</p>

                <div>
                  <div className="text-[11px] uppercase font-mono text-[#8b949e]">Discovered Lookalike Organizations:</div>
                  <div className="mt-1 space-y-1">
                    {recoveryOutput.lookalike_companies?.map((c: any, i: number) => (
                      <div key={i} className="text-xs text-white flex items-center justify-between p-2 rounded bg-[#161b22] border border-[#30363d]">
                        <span>{c.name}</span>
                        <span className="text-[11px] text-[#2ea043]">{c.match_reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div className="p-5 rounded-xl bg-[#161b22] border border-[#30363d]">
              <h4 className="text-sm font-bold text-white mb-3">Rejection Recovery Log</h4>
              {rejectionLogs.length === 0 ? (
                <div className="text-xs text-[#8b949e]">No rejection records logged yet.</div>
              ) : (
                <div className="space-y-3">
                  {rejectionLogs.map((log) => (
                    <div key={log.id} className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d] text-xs">
                      <div className="text-[#8b949e] italic">&ldquo;{log.rejection_reason}&rdquo;</div>
                      <div className="mt-2 text-[#58a6ff] font-medium flex items-center gap-1">
                        <Sparkles className="w-3 h-3" />
                        <span>{log.lookalike_companies?.length || 0} Lookalike Opportunities Discovered</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: Profile & Resume Parser */}
      {activeTab === 'profile' && (
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Resume Parser */}
          <div className="p-6 rounded-xl bg-[#161b22] border border-[#30363d] space-y-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#58a6ff]">
              <FileText className="w-3.5 h-3.5" />
              AI Resume Parser
            </div>
            <h3 className="text-lg font-bold text-white">Extract Skills &amp; Align Strategy</h3>
            <p className="text-xs text-[#8b949e]">
              Paste your raw CV, project history, or markdown summary. The ProfileAnalyzerAgent extracts tech stacks and auto-populates your career targets.
            </p>

            <textarea
              rows={6}
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              placeholder="Paste resume markdown or plain text here…"
              className="w-full px-3 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-xs focus:outline-none focus:border-[#1f6feb]"
            />

            {parseMessage && (
              <div className="p-3 bg-[#0d1117] rounded-xl border border-[#2ea043] text-xs text-[#2ea043]">
                {parseMessage}
              </div>
            )}

            <button
              onClick={handleParseResume}
              disabled={isParsingResume || !resumeText.trim()}
              className="w-full py-2.5 bg-[#1f6feb] hover:bg-[#388bfd] disabled:opacity-50 text-white font-semibold rounded-xl text-xs transition-all flex items-center justify-center gap-2"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{isParsingResume ? 'Extracting Resume Signals…' : 'Parse & Update Profile'}</span>
            </button>
          </div>

          {/* Profile Editor */}
          <div className="p-6 rounded-xl bg-[#161b22] border border-[#30363d] space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-white">Candidate Parameters</h3>
              <button
                onClick={() => setIsEditingProfile(!isEditingProfile)}
                className="text-xs text-[#58a6ff] hover:underline"
              >
                {isEditingProfile ? 'Cancel' : 'Edit Fields'}
              </button>
            </div>

            <form onSubmit={handleUpdateProfile} className="space-y-3 text-xs">
              <div>
                <label className="block text-[#8b949e] mb-1">Headline / Target Role</label>
                <input
                  type="text"
                  disabled={!isEditingProfile}
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-white disabled:opacity-60"
                />
              </div>

              <div>
                <label className="block text-[#8b949e] mb-1">Skills (Comma-separated)</label>
                <input
                  type="text"
                  disabled={!isEditingProfile}
                  value={editSkills}
                  onChange={(e) => setEditSkills(e.target.value)}
                  className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-white disabled:opacity-60"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#8b949e] mb-1">Min Salary ($)</label>
                  <input
                    type="number"
                    disabled={!isEditingProfile}
                    value={editSalaryMin}
                    onChange={(e) => setEditSalaryMin(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-white disabled:opacity-60"
                  />
                </div>
                <div>
                  <label className="block text-[#8b949e] mb-1">Max Salary ($)</label>
                  <input
                    type="number"
                    disabled={!isEditingProfile}
                    value={editSalaryMax}
                    onChange={(e) => setEditSalaryMax(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-white disabled:opacity-60"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[#8b949e] mb-1">Career Goal Alignment</label>
                <textarea
                  rows={2}
                  disabled={!isEditingProfile}
                  value={editGoals}
                  onChange={(e) => setEditGoals(e.target.value)}
                  className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-white disabled:opacity-60"
                />
              </div>

              {isEditingProfile && (
                <button
                  type="submit"
                  className="w-full py-2 bg-[#238636] hover:bg-[#2ea043] text-white font-semibold rounded-lg text-xs"
                >
                  Save Profile Updates
                </button>
              )}
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
