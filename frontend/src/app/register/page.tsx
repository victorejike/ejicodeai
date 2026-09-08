'use client';

import { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Users,
  Building2,
  Lock,
  Mail,
  User,
  Globe,
  Briefcase,
  MapPin,
  ArrowRight,
  ShieldCheck,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Eye,
} from 'lucide-react';

function RegisterContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [accountType, setAccountType] = useState<'individual' | 'enterprise'>('individual');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [title, setTitle] = useState('');
  const [skillsStr, setSkillsStr] = useState('Python, FastAPI, React, PostgreSQL');
  const [location, setLocation] = useState('Remote');
  const [remotePreference, setRemotePreference] = useState('remote');

  // Enterprise specific
  const [orgName, setOrgName] = useState('');
  const [domain, setDomain] = useState('');
  const [planTier, setPlanTier] = useState('scale');

  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const typeParam = searchParams.get('type');
    if (typeParam === 'enterprise' || typeParam === 'individual') {
      setAccountType(typeParam);
    }
  }, [searchParams]);

  const isIndividual = accountType === 'individual';
  const trackAccentColor = isIndividual ? 'text-blue-400' : 'text-emerald-400';
  const trackGlowColor = isIndividual ? 'bg-blue-600/[0.08]' : 'bg-emerald-600/[0.08]';
  const trackBorder = isIndividual
    ? 'focus:border-blue-400/70 focus:ring-1 focus:ring-blue-400/30'
    : 'focus:border-emerald-400/70 focus:ring-1 focus:ring-emerald-400/30';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      const payload: any = {
        account_type: accountType,
        email,
        password,
        full_name: fullName,
      };

      if (accountType === 'individual') {
        payload.title = title || 'Software Engineer';
        payload.skills = skillsStr
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean);
        payload.location = location;
        payload.remote_preference = remotePreference;
      } else {
        payload.organization_name = orgName;
        payload.domain = domain || email.split('@')[1];
        payload.plan_tier = planTier;
      }

      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Registration failed');
      }

      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('account_type', accountType);
      }

      if (accountType === 'individual') {
        router.push('/individual/profile');
      } else {
        router.push('/enterprise/profile');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'An error occurred during registration.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#000000] text-[#f4f4f5] selection:bg-white selection:text-black relative overflow-x-hidden font-sans flex flex-col justify-between">
      {/* Dynamic Ambient Background Glows */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="w-[800px] h-[800px] bg-red-600/[0.10] blur-[160px] animate-aurora rounded-full absolute -top-40 left-1/4" />
        <div className={`w-[650px] h-[650px] ${trackGlowColor} blur-[150px] animate-aurora-red rounded-full absolute top-1/3 -right-40 transition-colors duration-700`} />
        <div className="w-[500px] h-[500px] bg-emerald-600/[0.04] blur-[140px] animate-aurora rounded-full absolute -bottom-20 left-10" />
      </div>

      {/* Floating Apple-Glass Header Pill */}
      <header className="fixed top-5 inset-x-0 mx-auto max-w-5xl z-50 px-4">
        <div className="apple-glass-pill px-5 py-3 flex items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-3 group shrink-0">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-white/90 via-white/70 to-white/40 flex items-center justify-center text-black font-mono font-black text-xs shadow-md shadow-white/10 group-hover:scale-105 transition-transform">
              E
            </div>
            <span className="font-mono font-bold tracking-tight text-white text-sm hidden sm:inline">
              EJICODE_AI
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-xs text-zinc-400 font-medium">
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            <Link href="/#individuals" className="hover:text-white transition-colors">Individuals</Link>
            <Link href="/#enterprises" className="hover:text-white transition-colors">Enterprises</Link>
            <Link href="/#trust" className="hover:text-white transition-colors">Trust &amp; Data</Link>
          </nav>

          <div className="flex items-center gap-2 shrink-0">
            <Link
              href="/login"
              className="apple-button-secondary px-3.5 py-1.5 text-xs font-semibold whitespace-nowrap"
            >
              Sign In
            </Link>
          </div>
        </div>
      </header>

      {/* Main Form Area */}
      <main className="relative z-10 flex-1 flex flex-col justify-center items-center pt-32 pb-12 px-4 sm:px-6 lg:px-8">
        <div className="w-full max-w-xl mx-auto text-center mb-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full apple-glass-subtle text-xs text-zinc-300 font-medium mb-3 animate-float">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span>Autonomous AI Workspace Registration</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-white leading-tight">
            Create your <span className="text-gradient-apple-glow font-bold">Workspace</span>
          </h1>
          <p className="mt-2 text-xs sm:text-sm text-zinc-400 max-w-sm mx-auto leading-relaxed">
            Individual and Enterprise workspaces operate on verified real-world data and dedicated agents.
          </p>
        </div>

        <div className="w-full max-w-xl mx-auto">
          <div className="apple-glass p-6 sm:p-9 rounded-3xl shadow-2xl border border-white/10 relative overflow-hidden backdrop-blur-3xl">
            {/* Ambient accent inside card */}
            <div
              className={`absolute top-0 right-0 w-48 h-48 ${
                isIndividual ? 'bg-blue-600/10' : 'bg-emerald-600/10'
              } blur-[60px] pointer-events-none rounded-full transition-colors duration-500`}
            />

            {/* Track Switcher */}
            <div className="grid grid-cols-2 gap-1.5 p-1 bg-black/50 rounded-2xl border border-white/10 mb-6">
              <button
                type="button"
                onClick={() => setAccountType('individual')}
                className={`flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isIndividual
                    ? 'bg-blue-500 text-white shadow-md font-bold'
                    : 'text-zinc-400 hover:text-white'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                <span>Individual Candidate</span>
              </button>
              <button
                type="button"
                onClick={() => setAccountType('enterprise')}
                className={`flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  !isIndividual
                    ? 'bg-emerald-500 text-white shadow-md font-bold'
                    : 'text-zinc-400 hover:text-white'
                }`}
              >
                <Building2 className="w-3.5 h-3.5" />
                <span>Enterprise Org</span>
              </button>
            </div>

            {errorMsg && (
              <div className="mb-6 p-4 rounded-2xl bg-red-950/40 border border-red-500/30 flex items-start gap-3 text-red-200 text-xs">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-400 mt-0.5" />
                <div>{errorMsg}</div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                  Full Name
                </label>
                <div className="relative">
                  <User className="w-4 h-4 absolute left-3.5 top-3 text-zinc-500" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Jane Doe"
                    className={`w-full pl-10 pr-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white text-sm placeholder-zinc-500 focus:outline-none ${trackBorder} transition-all`}
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                  {isIndividual ? 'Email Address' : 'Work Email Address'}
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 absolute left-3.5 top-3 text-zinc-500" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={isIndividual ? 'jane@gmail.com' : 'jane@acmecorp.com'}
                    className={`w-full pl-10 pr-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white text-sm placeholder-zinc-500 focus:outline-none ${trackBorder} transition-all`}
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 absolute left-3.5 top-3 text-zinc-500" />
                  <input
                    type="password"
                    required
                    minLength={6}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className={`w-full pl-10 pr-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white text-sm placeholder-zinc-500 focus:outline-none ${trackBorder} transition-all`}
                  />
                </div>
              </div>

              {/* Individual Fields */}
              {isIndividual && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                      Target Role / Headline
                    </label>
                    <div className="relative">
                      <Briefcase className="w-4 h-4 absolute left-3.5 top-3 text-zinc-500" />
                      <input
                        type="text"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        placeholder="e.g. Senior AI Platform Engineer"
                        className={`w-full pl-10 pr-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white text-sm placeholder-zinc-500 focus:outline-none ${trackBorder} transition-all`}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                      Primary Skills (Comma-separated)
                    </label>
                    <input
                      type="text"
                      value={skillsStr}
                      onChange={(e) => setSkillsStr(e.target.value)}
                      placeholder="Python, FastAPI, React, Docker, Kubernetes"
                      className={`w-full px-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white text-sm placeholder-zinc-500 focus:outline-none ${trackBorder} transition-all`}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                        Location
                      </label>
                      <div className="relative">
                        <MapPin className="w-4 h-4 absolute left-3.5 top-3 text-zinc-500" />
                        <input
                          type="text"
                          value={location}
                          onChange={(e) => setLocation(e.target.value)}
                          placeholder="Remote or City"
                          className={`w-full pl-10 pr-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white text-sm placeholder-zinc-500 focus:outline-none ${trackBorder} transition-all`}
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                        Preference
                      </label>
                      <select
                        value={remotePreference}
                        onChange={(e) => setRemotePreference(e.target.value)}
                        className={`w-full px-3 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white text-sm focus:outline-none ${trackBorder} transition-all`}
                      >
                        <option value="remote">Remote Only</option>
                        <option value="hybrid">Hybrid</option>
                        <option value="onsite">Onsite</option>
                        <option value="any">Any Work Mode</option>
                      </select>
                    </div>
                  </div>
                </>
              )}

              {/* Enterprise Fields */}
              {!isIndividual && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                      Organization / Company Name
                    </label>
                    <div className="relative">
                      <Building2 className="w-4 h-4 absolute left-3.5 top-3 text-zinc-500" />
                      <input
                        type="text"
                        required
                        value={orgName}
                        onChange={(e) => setOrgName(e.target.value)}
                        placeholder="e.g. Acme Technologies Inc."
                        className={`w-full pl-10 pr-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white text-sm placeholder-zinc-500 focus:outline-none ${trackBorder} transition-all`}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                        Company Domain
                      </label>
                      <div className="relative">
                        <Globe className="w-4 h-4 absolute left-3.5 top-3 text-zinc-500" />
                        <input
                          type="text"
                          value={domain}
                          onChange={(e) => setDomain(e.target.value)}
                          placeholder="acmecorp.com"
                          className={`w-full pl-10 pr-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white text-sm placeholder-zinc-500 focus:outline-none ${trackBorder} transition-all`}
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                        Plan Tier
                      </label>
                      <select
                        value={planTier}
                        onChange={(e) => setPlanTier(e.target.value)}
                        className={`w-full px-3 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white text-sm focus:outline-none ${trackBorder} transition-all`}
                      >
                        <option value="pro">Pro Workspace</option>
                        <option value="scale">Scale Hiring (Recommended)</option>
                        <option value="enterprise">Enterprise Custom</option>
                      </select>
                    </div>
                  </div>
                </>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className={`w-full mt-3 py-3 px-4 font-semibold text-black rounded-full transition-all duration-300 shadow-lg flex items-center justify-center gap-2 ${
                  isIndividual
                    ? 'bg-gradient-to-r from-blue-400 to-white hover:opacity-90'
                    : 'bg-gradient-to-r from-emerald-400 to-white hover:opacity-90'
                } disabled:opacity-50 text-xs sm:text-sm hover:scale-[1.01]`}
              >
                <ShieldCheck className="w-4 h-4" />
                <span>
                  {isSubmitting
                    ? 'Creating Workspace…'
                    : isIndividual
                    ? 'Create Individual Account'
                    : 'Create Enterprise Workspace'}
                </span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>

            <div className="mt-6 pt-4 border-t border-white/10 text-center text-xs text-zinc-500">
              Already have an account?{' '}
              <Link href="/login" className={`${trackAccentColor} hover:underline font-semibold`}>
                Sign In
              </Link>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 px-4 border-t border-white/10 relative z-10 text-xs text-zinc-500">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-full bg-white flex items-center justify-center text-black font-mono font-bold text-[10px]">
              E
            </div>
            <span className="font-mono font-bold text-white">EJICODE_AI</span>
            <span>&copy; {new Date().getFullYear()} Autonomous Career Agents</span>
          </div>

          <div className="flex items-center gap-4 text-[11px]">
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            <Link href="/login" className="hover:text-white transition-colors">Sign In</Link>
            <Link href="/forgot-password" className="hover:text-white transition-colors">Forgot Password?</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-black flex items-center justify-center text-zinc-500 text-xs">Loading workspace setup...</div>}>
      <RegisterContent />
    </Suspense>
  );
}
