'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Sparkles,
  UploadCloud,
  FileUp,
  User,
  Briefcase,
  MapPin,
  Github,
  Linkedin,
  Globe,
  DollarSign,
  Target,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
  AlertCircle,
  ShieldCheck,
  GraduationCap,
  Award,
  FolderGit2,
  Calendar,
} from 'lucide-react';

interface ProfileData {
  full_name: string | null;
  title: string | null;
  bio: string | null;
  skills: string[];
  experience_years: number | null;
  experience?: Array<{
    title?: string;
    company?: string;
    start_date?: string;
    end_date?: string;
    is_current?: boolean;
    bullets?: string[];
  }>;
  education?: Array<{
    degree?: string;
    institution?: string;
    year?: number;
    details?: string;
  }>;
  certifications?: Array<{
    name?: string;
    issuer?: string;
    year?: number;
    details?: string;
  }>;
  projects?: Array<{
    name?: string;
    description?: string;
    tech_stack?: string[];
    url?: string;
  }>;
  location: string | null;
  remote_preference: string | null;
  salary_min: number | null;
  salary_max: number | null;
  portfolio_url: string | null;
  github_url: string | null;
  linkedin_url: string | null;
  career_goals: string | null;
  completion_percentage: number;
  has_cv: boolean;
  onboarding_complete: boolean;
}

export default function IndividualProfilePage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<ProfileData | null>(null);

  // Form fields
  const [fullName, setFullName] = useState('');
  const [title, setTitle] = useState('');
  const [bio, setBio] = useState('');
  const [skillsStr, setSkillsStr] = useState('');
  const [experienceYears, setExperienceYears] = useState('');
  const [location, setLocation] = useState('');
  const [remotePreference, setRemotePreference] = useState('remote');
  const [salaryMin, setSalaryMin] = useState('');
  const [salaryMax, setSalaryMax] = useState('');
  const [portfolioUrl, setPortfolioUrl] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [careerGoals, setCareerGoals] = useState('');

  const [isUploadingCv, setIsUploadingCv] = useState(false);
  const [cvMessage, setCvMessage] = useState<string | null>(null);
  const [cvError, setCvError] = useState<string | null>(null);

  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    const t = localStorage.getItem('token');
    if (!t) {
      router.replace('/login?type=individual');
      return;
    }
    setToken(t);
  }, [router]);

  const fetchProfile = async (authToken: string) => {
    setLoading(true);
    try {
      const res = await fetch('/api/individual/profile', {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      const data = await res.json();
      if (res.ok && data.profile) {
        const p: ProfileData = data.profile;
        setProfile(p);
        setFullName(p.full_name || '');
        setTitle(p.title || '');
        setBio(p.bio || '');
        setSkillsStr((p.skills || []).join(', '));
        setExperienceYears(p.experience_years != null ? String(p.experience_years) : '');
        setLocation(p.location || '');
        setRemotePreference(p.remote_preference || 'remote');
        setSalaryMin(p.salary_min != null ? String(p.salary_min) : '');
        setSalaryMax(p.salary_max != null ? String(p.salary_max) : '');
        setPortfolioUrl(p.portfolio_url || '');
        setGithubUrl(p.github_url || '');
        setLinkedinUrl(p.linkedin_url || '');
        setCareerGoals(p.career_goals || '');
      }
    } catch (err) {
      console.error('Failed to load profile:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchProfile(token);
  }, [token]);

  const handleCvUpload = async (file: File) => {
    if (!token) return;
    setIsUploadingCv(true);
    setCvMessage(null);
    setCvError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('/api/individual/cv/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || data.detail || 'CV upload failed');
      }

      const extractedSkillCount = Array.isArray(data.extracted_skills) ? data.extracted_skills.length : 0;
      setCvMessage(
        extractedSkillCount > 0
          ? `CV processed. ${extractedSkillCount} skill${extractedSkillCount === 1 ? '' : 's'} extracted and added to your profile.`
          : 'CV uploaded and stored. No skills could be confidently extracted \u2014 you can add them manually below.'
      );

      if (data.profile) {
        const p = data.profile;
        setProfile(p);
        if (p.full_name) setFullName(p.full_name);
        if (p.title) setTitle(p.title);
        if (p.bio) setBio(p.bio);
        if (p.skills) setSkillsStr((p.skills || []).join(', '));
        if (p.experience_years != null) setExperienceYears(String(p.experience_years));
        if (p.location) setLocation(p.location);
        if (p.career_goals) setCareerGoals(p.career_goals);
        if (p.portfolio_url) setPortfolioUrl(p.portfolio_url);
        if (p.github_url) setGithubUrl(p.github_url);
        if (p.linkedin_url) setLinkedinUrl(p.linkedin_url);
      }

      await fetchProfile(token);
    } catch (err: any) {
      setCvError(err.message || 'Failed to upload CV. Please try again.');
    } finally {
      setIsUploadingCv(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleCvUpload(file);
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setIsSaving(true);
    setSaveMessage(null);
    setSaveError(null);

    try {
      const skills = skillsStr
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);

      const payload: Record<string, any> = {
        full_name: fullName || undefined,
        title: title || undefined,
        bio: bio || undefined,
        skills,
        location: location || undefined,
        remote_preference: remotePreference,
        portfolio_url: portfolioUrl || undefined,
        github_url: githubUrl || undefined,
        linkedin_url: linkedinUrl || undefined,
        career_goals: careerGoals || undefined,
      };
      if (experienceYears !== '') payload.experience_years = Number(experienceYears);
      if (salaryMin !== '') payload.salary_min = Number(salaryMin);
      if (salaryMax !== '') payload.salary_max = Number(salaryMax);

      const res = await fetch('/api/individual/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || data.detail || 'Failed to save profile');
      }

      setSaveMessage('Profile saved. This is what EJICODE AI will use to search for real opportunities.');
      await fetchProfile(token);
    } catch (err: any) {
      setSaveError(err.message || 'Failed to save profile. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const readyForDiscovery = profile?.onboarding_complete ?? false;

  return (
    <div className="min-h-screen bg-black text-zinc-100 relative overflow-x-hidden">
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="w-[700px] h-[700px] bg-blue-600/[0.08] blur-[160px] animate-aurora rounded-full absolute -top-40 left-1/3" />
        <div className="w-[500px] h-[500px] bg-red-600/[0.05] blur-[140px] animate-aurora-red rounded-full absolute bottom-0 -right-20" />
      </div>

      {/* Header */}
      <header className="relative z-10 border-b border-white/10">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-white/90 via-white/70 to-white/40 flex items-center justify-center text-black font-mono font-black text-xs">
              E
            </div>
            <span className="font-mono font-bold tracking-tight text-white text-sm">EJICODE_AI</span>
          </Link>
          {readyForDiscovery && (
            <Link
              href="/individual/dashboard"
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
          <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full apple-glass-subtle text-xs text-blue-300 font-medium mb-5">
            <Target className="w-3.5 h-3.5" />
            <span>Step 1 &middot; Build your intelligence profile</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
            This is your AI knowledge base.
          </h1>
          <p className="mt-3 text-sm text-zinc-400 max-w-2xl leading-relaxed">
            EJICODE AI only searches the internet for jobs and client work once it knows who you actually are.
            Upload your CV, or enter your skills and experience below &mdash; nothing is invented, and nothing
            is searched for until this is real.
          </p>
        </div>

        {loading ? (
          <div className="apple-glass rounded-3xl p-10 text-center text-zinc-500 text-sm flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin" />
            Loading your profile…
          </div>
        ) : (
          <div className="space-y-6">
            {/* Completion status */}
            <div className="apple-glass-subtle rounded-2xl p-4 flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                {readyForDiscovery ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-amber-400 shrink-0" />
                )}
                <div>
                  <div className="text-sm font-semibold text-white">
                    {readyForDiscovery ? 'Profile ready for AI discovery' : 'Profile incomplete'}
                  </div>
                  <div className="text-xs text-zinc-500">
                    {readyForDiscovery
                      ? 'EJICODE AI can now search for real opportunities that match you.'
                      : 'Upload a CV or add a title and at least one skill to activate discovery.'}
                  </div>
                </div>
              </div>
              <div className="text-xs font-mono text-zinc-400">
                {profile?.completion_percentage ?? 0}% complete
              </div>
            </div>

            {/* CV Upload */}
            <div className="apple-glass rounded-3xl p-6 sm:p-8">
              <div className="flex items-center gap-2.5 mb-1">
                <UploadCloud className="w-4 h-4 text-blue-400" />
                <h2 className="text-sm font-bold text-white uppercase tracking-wide">Upload your CV / Resume</h2>
              </div>
              <p className="text-xs text-zinc-500 mb-4">
                PDF, DOCX, or TXT. We extract your real skills, experience, and education \u2014 nothing is fabricated,
                and anything we can't confidently read is left blank rather than guessed.
              </p>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.doc,.docx,.txt"
                className="hidden"
                onChange={handleFileChange}
              />

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploadingCv}
                className="w-full border border-dashed border-white/20 hover:border-blue-400/50 rounded-2xl py-8 flex flex-col items-center justify-center gap-2 text-zinc-400 hover:text-white transition-colors disabled:opacity-50"
              >
                {isUploadingCv ? (
                  <>
                    <RefreshCw className="w-6 h-6 animate-spin text-blue-400" />
                    <span className="text-xs">Reading and extracting your CV…</span>
                  </>
                ) : (
                  <>
                    <FileUp className="w-6 h-6" />
                    <span className="text-xs font-medium">Click to select a file, or drag it here</span>
                  </>
                )}
              </button>

              {profile?.has_cv && !isUploadingCv && (
                <div className="mt-3 text-xs text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  A CV is already on file. Uploading a new one will replace the extracted data.
                </div>
              )}

              {cvMessage && (
                <div className="mt-3 p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-200 text-xs">
                  {cvMessage}
                </div>
              )}
              {cvError && (
                <div className="mt-3 p-3 rounded-xl bg-red-950/40 border border-red-500/30 text-red-200 text-xs flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  {cvError}
                </div>
              )}
            </div>

            {/* Extracted Career Intelligence Bento (Rendered when CV has been ingested) */}
            {profile && (profile.experience?.length || profile.education?.length || profile.certifications?.length || profile.projects?.length) ? (
              <div className="apple-glass rounded-3xl p-6 sm:p-8 space-y-6">
                <div className="flex items-center justify-between border-b border-white/10 pb-4">
                  <div className="flex items-center gap-2.5">
                    <Sparkles className="w-4 h-4 text-emerald-400" />
                    <h2 className="text-sm font-bold text-white uppercase tracking-wide">Extracted CV Intelligence</h2>
                  </div>
                  <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
                    Factual &bull; Zero Hallucination
                  </span>
                </div>

                {/* Work Experience */}
                {profile.experience && profile.experience.length > 0 && (
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-xs font-semibold text-zinc-300">
                      <Briefcase className="w-3.5 h-3.5 text-blue-400" />
                      <span>Work Experience ({profile.experience.length})</span>
                    </div>
                    <div className="grid gap-3">
                      {profile.experience.map((exp, idx) => (
                        <div key={idx} className="p-4 rounded-2xl bg-white/[0.03] border border-white/5 space-y-1.5">
                          <div className="flex items-center justify-between flex-wrap gap-2">
                            <span className="text-sm font-bold text-white">{exp.title}</span>
                            {(exp.start_date || exp.end_date) && (
                              <span className="text-[11px] font-mono text-zinc-400 flex items-center gap-1">
                                <Calendar className="w-3 h-3 text-zinc-500" />
                                {exp.start_date} {exp.end_date ? `— ${exp.end_date}` : ''}
                              </span>
                            )}
                          </div>
                          {exp.company && (
                            <div className="text-xs text-blue-300 font-medium">{exp.company}</div>
                          )}
                          {exp.bullets && exp.bullets.length > 0 && (
                            <ul className="list-disc list-inside text-xs text-zinc-400 space-y-1 pt-1 pl-1">
                              {exp.bullets.slice(0, 3).map((b, bIdx) => (
                                <li key={bIdx} className="leading-relaxed">{b}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Education & Certifications Grid */}
                <div className="grid sm:grid-cols-2 gap-4">
                  {/* Education */}
                  {profile.education && profile.education.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-xs font-semibold text-zinc-300">
                        <GraduationCap className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Education</span>
                      </div>
                      <div className="space-y-2">
                        {profile.education.map((edu, idx) => (
                          <div key={idx} className="p-3 rounded-xl bg-white/[0.03] border border-white/5 text-xs">
                            <div className="font-semibold text-white">{edu.degree}</div>
                            <div className="text-zinc-400">{edu.institution} {edu.year ? `(${edu.year})` : ''}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Certifications */}
                  {profile.certifications && profile.certifications.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-xs font-semibold text-zinc-300">
                        <Award className="w-3.5 h-3.5 text-amber-400" />
                        <span>Certifications</span>
                      </div>
                      <div className="space-y-2">
                        {profile.certifications.map((cert, idx) => (
                          <div key={idx} className="p-3 rounded-xl bg-white/[0.03] border border-white/5 text-xs">
                            <div className="font-semibold text-white">{cert.name}</div>
                            <div className="text-zinc-400">{cert.issuer} {cert.year ? `(${cert.year})` : ''}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Projects */}
                {profile.projects && profile.projects.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-zinc-300">
                      <FolderGit2 className="w-3.5 h-3.5 text-purple-400" />
                      <span>Projects</span>
                    </div>
                    <div className="grid sm:grid-cols-2 gap-3">
                      {profile.projects.map((proj, idx) => (
                        <div key={idx} className="p-3 rounded-xl bg-white/[0.03] border border-white/5 text-xs space-y-1">
                          <div className="font-semibold text-white">{proj.name}</div>
                          {proj.description && <div className="text-zinc-400 text-[11px] line-clamp-2">{proj.description}</div>}
                          {proj.url && (
                            <a href={proj.url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline text-[11px] block truncate">
                              {proj.url}
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : null}

            {/* Manual profile form */}
            <form onSubmit={handleSaveProfile} className="apple-glass rounded-3xl p-6 sm:p-8 space-y-5">
              <div className="flex items-center gap-2.5">
                <User className="w-4 h-4 text-blue-400" />
                <h2 className="text-sm font-bold text-white uppercase tracking-wide">Profile Parameters</h2>
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Full Name</label>
                  <div className="relative">
                    <User className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="e.g. Victor Ejike"
                      className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-400/50"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Professional Title / Headline</label>
                  <div className="relative">
                    <Briefcase className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="e.g. Senior Backend Engineer"
                      className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-400/50"
                    />
                  </div>
                </div>
              </div>

              <div className="grid sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Years of Experience</label>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={experienceYears}
                    onChange={(e) => setExperienceYears(e.target.value)}
                    placeholder="e.g. 4"
                    className="w-full px-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-400/50"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Location</label>
                  <div className="relative">
                    <MapPin className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="text"
                      value={location}
                      onChange={(e) => setLocation(e.target.value)}
                      placeholder="City, Country or Remote"
                      className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-400/50"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Work Preference</label>
                  <select
                    value={remotePreference}
                    onChange={(e) => setRemotePreference(e.target.value)}
                    className="w-full px-3 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-400/50"
                  >
                    <option value="remote">Remote Only</option>
                    <option value="hybrid">Hybrid</option>
                    <option value="onsite">Onsite</option>
                    <option value="any">Any Work Mode</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">Skills (comma-separated)</label>
                <input
                  type="text"
                  value={skillsStr}
                  onChange={(e) => setSkillsStr(e.target.value)}
                  placeholder="e.g. Python, FastAPI, PostgreSQL, React"
                  className="w-full px-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-400/50"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">Short Bio</label>
                <textarea
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                  rows={3}
                  placeholder="A couple of sentences about your background."
                  className="w-full px-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-400/50 resize-none"
                />
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Minimum Rate / Salary (optional)</label>
                  <div className="relative">
                    <DollarSign className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="number"
                      min="0"
                      value={salaryMin}
                      onChange={(e) => setSalaryMin(e.target.value)}
                      placeholder="Leave blank if unsure"
                      className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-400/50"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Maximum Rate / Salary (optional)</label>
                  <div className="relative">
                    <DollarSign className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="number"
                      min="0"
                      value={salaryMax}
                      onChange={(e) => setSalaryMax(e.target.value)}
                      placeholder="Leave blank if unsure"
                      className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-400/50"
                    />
                  </div>
                </div>
              </div>

              <div className="grid sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">Portfolio URL</label>
                  <div className="relative">
                    <Globe className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="url"
                      value={portfolioUrl}
                      onChange={(e) => setPortfolioUrl(e.target.value)}
                      placeholder="https://"
                      className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-400/50"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">GitHub URL</label>
                  <div className="relative">
                    <Github className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="url"
                      value={githubUrl}
                      onChange={(e) => setGithubUrl(e.target.value)}
                      placeholder="https://github.com/…"
                      className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-400/50"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">LinkedIn URL</label>
                  <div className="relative">
                    <Linkedin className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="url"
                      value={linkedinUrl}
                      onChange={(e) => setLinkedinUrl(e.target.value)}
                      placeholder="https://linkedin.com/in/…"
                      className="w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-400/50"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">Career Goals</label>
                <textarea
                  value={careerGoals}
                  onChange={(e) => setCareerGoals(e.target.value)}
                  rows={2}
                  placeholder="What kind of role or client work are you looking for?"
                  className="w-full px-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-400/50 resize-none"
                />
              </div>

              {saveMessage && (
                <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-200 text-xs">
                  {saveMessage}
                </div>
              )}
              {saveError && (
                <div className="p-3 rounded-xl bg-red-950/40 border border-red-500/30 text-red-200 text-xs flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  {saveError}
                </div>
              )}

              <div className="flex flex-wrap items-center gap-3 pt-2">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="bg-blue-500 hover:bg-blue-400 disabled:opacity-50 text-white text-sm font-semibold rounded-full px-6 py-3 flex items-center gap-2 shadow-md shadow-blue-500/25 transition-all"
                >
                  <ShieldCheck className="w-4 h-4" />
                  {isSaving ? 'Saving…' : 'Save Profile'}
                </button>

                <Link
                  href="/individual/dashboard"
                  aria-disabled={!readyForDiscovery}
                  onClick={(e) => {
                    if (!readyForDiscovery) e.preventDefault();
                  }}
                  className={`text-sm font-semibold rounded-full px-6 py-3 flex items-center gap-2 transition-all ${
                    readyForDiscovery
                      ? 'apple-button-secondary'
                      : 'bg-white/5 text-zinc-600 cursor-not-allowed border border-white/5'
                  }`}
                >
                  <span>Continue to Dashboard</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>

                {!readyForDiscovery && (
                  <span className="text-xs text-zinc-500 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    Save a title + skill, or upload a CV, to unlock your dashboard.
                  </span>
                )}
              </div>
            </form>
          </div>
        )}
      </main>
    </div>
  );
}
