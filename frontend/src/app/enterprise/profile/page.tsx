'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Building2,
  Globe,
  Factory,
  Users,
  FileText,
  ListChecks,
  MapPin,
  DollarSign,
  Briefcase,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Trash2,
} from 'lucide-react';

const API_URL = 'http://localhost:8000';

interface Requirement {
  id: string;
  title: string;
  raw_description: string;
  required_skills: string[];
  min_experience_years: number | null;
  location_type: string | null;
  status: string;
  created_at: string | null;
}

export default function EnterpriseProfilePage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [onboardingComplete, setOnboardingComplete] = useState(false);

  // Organization fields
  const [orgName, setOrgName] = useState('');
  const [domain, setDomain] = useState('');
  const [industry, setIndustry] = useState('');
  const [companySize, setCompanySize] = useState('');
  const [description, setDescription] = useState('');
  const [isSavingOrg, setIsSavingOrg] = useState(false);
  const [orgMessage, setOrgMessage] = useState<string | null>(null);
  const [orgError, setOrgError] = useState<string | null>(null);

  // Requirement fields
  const [reqTitle, setReqTitle] = useState('');
  const [reqDescription, setReqDescription] = useState('');
  const [reqSkills, setReqSkills] = useState('');
  const [reqExperience, setReqExperience] = useState('');
  const [reqLocation, setReqLocation] = useState('Remote');
  const [reqEngagement, setReqEngagement] = useState('full-time');
  const [reqBudgetMin, setReqBudgetMin] = useState('');
  const [reqBudgetMax, setReqBudgetMax] = useState('');
  const [isSavingReq, setIsSavingReq] = useState(false);
  const [reqMessage, setReqMessage] = useState<string | null>(null);
  const [reqError, setReqError] = useState<string | null>(null);

  const [requirements, setRequirements] = useState<Requirement[]>([]);

  useEffect(() => {
    const t = localStorage.getItem('token');
    if (!t) {
      router.replace('/login?type=enterprise');
      return;
    }
    setToken(t);
  }, [router]);

  const authHeaders = (t: string): Record<string, string> => ({ Authorization: `Bearer ${t}` });

  const fetchAll = async (authToken: string) => {
    setLoading(true);
    try {
      const orgRes = await fetch(`${API_URL}/v1/enterprise/organization`, {
        headers: authHeaders(authToken),
      });
      if (orgRes.ok) {
        const orgData = await orgRes.json();
        const org = orgData.organization;
        if (org) {
          setOrgName(org.name || '');
          setDomain(org.domain || '');
          const settings = org.settings || {};
          setIndustry(settings.industry || '');
          setCompanySize(settings.company_size || '');
          setDescription(settings.description || '');
          setOnboardingComplete(!!org.onboarding_complete);
        }
      }

      const reqRes = await fetch(`${API_URL}/v1/enterprise/requirements`, {
        headers: authHeaders(authToken),
      });
      if (reqRes.ok) {
        const reqData = await reqRes.json();
        setRequirements(Array.isArray(reqData.requirements) ? reqData.requirements : []);
      }
    } catch (err) {
      console.error('Failed to load organization profile:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchAll(token);
  }, [token]);

  const handleSaveOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setIsSavingOrg(true);
    setOrgMessage(null);
    setOrgError(null);

    try {
      const res = await fetch(`${API_URL}/v1/enterprise/organization`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({
          name: orgName || undefined,
          domain: domain || undefined,
          settings: {
            industry: industry || undefined,
            company_size: companySize || undefined,
            description: description || undefined,
          },
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || data.detail || 'Failed to save organization profile');
      }
      setOrgMessage('Organization profile saved.');
    } catch (err: any) {
      setOrgError(err.message || 'Failed to save organization profile.');
    } finally {
      setIsSavingOrg(false);
    }
  };

  const handleCreateRequirement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setIsSavingReq(true);
    setReqMessage(null);
    setReqError(null);

    try {
      const skillsArray = reqSkills.split(',').map((s) => s.trim()).filter(Boolean);
      const payload: Record<string, any> = {
        title: reqTitle,
        raw_description: reqDescription,
        required_skills: skillsArray.length > 0 ? skillsArray : undefined,
        location: reqLocation || 'Remote',
        engagement_type: reqEngagement,
      };
      if (reqExperience !== '') payload.min_experience_years = Number(reqExperience);
      if (reqBudgetMin !== '') payload.budget_min = Number(reqBudgetMin);
      if (reqBudgetMax !== '') payload.budget_max = Number(reqBudgetMax);

      const res = await fetch(`${API_URL}/v1/enterprise/requirements`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || data.detail || 'Failed to create requirement');
      }

      setReqMessage(`Requirement "${data.title}" created \u2014 this is now part of your discovery knowledge base.`);
      setReqTitle('');
      setReqDescription('');
      setReqSkills('');
      setReqExperience('');
      setReqBudgetMin('');
      setReqBudgetMax('');
      await fetchAll(token);
    } catch (err: any) {
      setReqError(err.message || 'Failed to create requirement.');
    } finally {
      setIsSavingReq(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-zinc-100 relative overflow-x-hidden">
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="w-[700px] h-[700px] bg-emerald-600/[0.08] blur-[160px] animate-aurora rounded-full absolute -top-40 left-1/3" />
        <div className="w-[500px] h-[500px] bg-red-600/[0.05] blur-[140px] animate-aurora-red rounded-full absolute bottom-0 -right-20" />
      </div>

      <header className="relative z-10 border-b border-white/10">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-white/90 via-white/70 to-white/40 flex items-center justify-center text-black font-mono font-black text-xs">
              E
            </div>
            <span className="font-mono font-bold tracking-tight text-white text-sm">EJICODE_AI</span>
          </Link>
          {onboardingComplete && (
            <Link
              href="/enterprise/dashboard"
              className="text-xs text-zinc-400 hover:text-white transition-colors flex items-center gap-1.5"
            >
              Skip to dashboard
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>
      </header>

      <main className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
        <div className="mb-8">
          <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full apple-glass-subtle text-xs text-emerald-300 font-medium mb-5">
            <ListChecks className="w-3.5 h-3.5" />
            <span>Step 1 &middot; Build your discovery knowledge base</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
            Tell EJICODE AI who you need.
          </h1>
          <p className="mt-3 text-sm text-zinc-400 max-w-2xl leading-relaxed">
            Discovery only starts once you've described a real requirement. Fill in your organization details
            and at least one role or client need below &mdash; that's what the AI searches, validates, and ranks
            candidates against.
          </p>
        </div>

        {loading ? (
          <div className="apple-glass rounded-3xl p-10 text-center text-zinc-500 text-sm flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin" />
            Loading your organization profile…
          </div>
        ) : (
          <div className="space-y-6">
            {/* Completion status */}
            <div className="apple-glass-subtle rounded-2xl p-4 flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                {onboardingComplete ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-amber-400 shrink-0" />
                )}
                <div>
                  <div className="text-sm font-semibold text-white">
                    {onboardingComplete ? 'Ready for talent discovery' : 'No requirements yet'}
                  </div>
                  <div className="text-xs text-zinc-500">
                    {onboardingComplete
                      ? 'EJICODE AI can now search for real candidates that match your requirements.'
                      : 'Add at least one requirement below to activate discovery.'}
                  </div>
                </div>
              </div>
              <div className="text-xs font-mono text-zinc-400">
                {requirements.length} requirement{requirements.length === 1 ? '' : 's'}
              </div>
            </div>

            {/* Organization details */}
            <form onSubmit={handleSaveOrg} className="apple-glass rounded-3xl p-6 sm:p-8 space-y-5">
              <div className="flex items-center gap-2.5">
                <Building2 className="w-4 h-4 text-emerald-400" />
                <h2 className="text-sm font-bold text-white uppercase tracking-wide">Organization Details</h2>
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Organization Name</label>
                  <div className="relative">
                    <Building2 className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="text"
                      value={orgName}
                      onChange={(e) => setOrgName(e.target.value)}
                      placeholder="e.g. Acme Technologies Inc."
                      className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-emerald-400/50"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Company Domain</label>
                  <div className="relative">
                    <Globe className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="text"
                      value={domain}
                      onChange={(e) => setDomain(e.target.value)}
                      placeholder="acmecorp.com"
                      className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-emerald-400/50"
                    />
                  </div>
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Industry</label>
                  <div className="relative">
                    <Factory className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="text"
                      value={industry}
                      onChange={(e) => setIndustry(e.target.value)}
                      placeholder="e.g. Fintech, HealthTech, AI/SaaS"
                      className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-emerald-400/50"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Company Size</label>
                  <div className="relative">
                    <Users className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="text"
                      value={companySize}
                      onChange={(e) => setCompanySize(e.target.value)}
                      placeholder="e.g. 11-50 employees"
                      className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-emerald-400/50"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">What does your organization do?</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  placeholder="A short description that helps the AI understand your business context."
                  className="w-full px-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-emerald-400/50 resize-none"
                />
              </div>

              {orgMessage && (
                <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-200 text-xs">
                  {orgMessage}
                </div>
              )}
              {orgError && (
                <div className="p-3 rounded-xl bg-red-950/40 border border-red-500/30 text-red-200 text-xs flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  {orgError}
                </div>
              )}

              <button
                type="submit"
                disabled={isSavingOrg}
                className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-white text-sm font-semibold rounded-full px-6 py-3 flex items-center gap-2 shadow-md shadow-emerald-500/25 transition-all"
              >
                <ShieldCheck className="w-4 h-4" />
                {isSavingOrg ? 'Saving…' : 'Save Organization Details'}
              </button>
            </form>

            {/* Talent Requirement */}
            <form onSubmit={handleCreateRequirement} className="apple-glass rounded-3xl p-6 sm:p-8 space-y-5">
              <div className="flex items-center gap-2.5">
                <FileText className="w-4 h-4 text-emerald-400" />
                <h2 className="text-sm font-bold text-white uppercase tracking-wide">
                  What are you hiring for, or what client work are you seeking?
                </h2>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">Role / Requirement Title</label>
                <div className="relative">
                  <Briefcase className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                  <input
                    type="text"
                    required
                    value={reqTitle}
                    onChange={(e) => setReqTitle(e.target.value)}
                    placeholder="e.g. Senior Backend Engineer, or Fintech clients needing payments infra"
                    className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-emerald-400/50"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">Describe what you need</label>
                <textarea
                  required
                  minLength={10}
                  value={reqDescription}
                  onChange={(e) => setReqDescription(e.target.value)}
                  rows={4}
                  placeholder="Be specific: the problem you're solving, must-have skills, seniority, and timeline."
                  className="w-full px-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-emerald-400/50 resize-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">Required Skills (comma-separated)</label>
                <input
                  type="text"
                  value={reqSkills}
                  onChange={(e) => setReqSkills(e.target.value)}
                  placeholder="e.g. Go, Kubernetes, PostgreSQL"
                  className="w-full px-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-emerald-400/50"
                />
                <p className="text-[11px] text-zinc-500 mt-1.5">
                  Leave blank and the AI will extract skills from your description \u2014 it will never invent
                  skills you didn't ask for.
                </p>
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Minimum Experience (years)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={reqExperience}
                    onChange={(e) => setReqExperience(e.target.value)}
                    placeholder="e.g. 4"
                    className="w-full px-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-emerald-400/50"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Location</label>
                  <div className="relative">
                    <MapPin className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="text"
                      value={reqLocation}
                      onChange={(e) => setReqLocation(e.target.value)}
                      placeholder="Remote or City"
                      className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-emerald-400/50"
                    />
                  </div>
                </div>
              </div>

              <div className="grid sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Engagement Type</label>
                  <select
                    value={reqEngagement}
                    onChange={(e) => setReqEngagement(e.target.value)}
                    className="w-full px-3 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-emerald-400/50"
                  >
                    <option value="full-time">Full-time</option>
                    <option value="contract">Contract</option>
                    <option value="freelance">Freelance</option>
                    <option value="fractional">Fractional</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Budget Min (optional)</label>
                  <div className="relative">
                    <DollarSign className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="number"
                      min="0"
                      value={reqBudgetMin}
                      onChange={(e) => setReqBudgetMin(e.target.value)}
                      placeholder="Leave blank if unsure"
                      className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-emerald-400/50"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Budget Max (optional)</label>
                  <div className="relative">
                    <DollarSign className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="number"
                      min="0"
                      value={reqBudgetMax}
                      onChange={(e) => setReqBudgetMax(e.target.value)}
                      placeholder="Leave blank if unsure"
                      className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-emerald-400/50"
                    />
                  </div>
                </div>
              </div>

              {reqMessage && (
                <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-200 text-xs">
                  {reqMessage}
                </div>
              )}
              {reqError && (
                <div className="p-3 rounded-xl bg-red-950/40 border border-red-500/30 text-red-200 text-xs flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  {reqError}
                </div>
              )}

              <div className="flex flex-wrap items-center gap-3 pt-2">
                <button
                  type="submit"
                  disabled={isSavingReq}
                  className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-white text-sm font-semibold rounded-full px-6 py-3 flex items-center gap-2 shadow-md shadow-emerald-500/25 transition-all"
                >
                  <ShieldCheck className="w-4 h-4" />
                  {isSavingReq ? 'Creating…' : 'Add Requirement'}
                </button>

                <Link
                  href="/enterprise/dashboard"
                  aria-disabled={!onboardingComplete}
                  onClick={(e) => {
                    if (!onboardingComplete) e.preventDefault();
                  }}
                  className={`text-sm font-semibold rounded-full px-6 py-3 flex items-center gap-2 transition-all ${
                    onboardingComplete
                      ? 'apple-button-secondary'
                      : 'bg-white/5 text-zinc-600 cursor-not-allowed border border-white/5'
                  }`}
                >
                  <span>Continue to Dashboard</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>

                {!onboardingComplete && (
                  <span className="text-xs text-zinc-500 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    Add at least one requirement to unlock your dashboard.
                  </span>
                )}
              </div>
            </form>

            {/* Existing requirements list */}
            {requirements.length > 0 && (
              <div className="apple-glass rounded-3xl p-6 sm:p-8">
                <div className="flex items-center gap-2.5 mb-4">
                  <ListChecks className="w-4 h-4 text-emerald-400" />
                  <h2 className="text-sm font-bold text-white uppercase tracking-wide">Your Requirements</h2>
                </div>
                <div className="space-y-3">
                  {requirements.map((r) => (
                    <div key={r.id} className="apple-glass-subtle rounded-2xl p-4">
                      <div className="flex items-center justify-between gap-3">
                        <h3 className="text-sm font-bold text-white">{r.title}</h3>
                        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0">
                          {r.status}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400 mt-1.5 leading-relaxed">{r.raw_description}</p>
                      {r.required_skills && r.required_skills.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2.5">
                          {r.required_skills.map((s) => (
                            <span key={s} className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/5 text-zinc-300 border border-white/10">
                              {s}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
