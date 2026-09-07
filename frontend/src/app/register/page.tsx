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
  const accentText = isIndividual ? 'text-blue-400' : 'text-emerald-400';
  const accentBorder = isIndividual ? 'focus:border-blue-400/50' : 'focus:border-emerald-400/50';
  const accentButton = isIndividual
    ? 'bg-blue-500 hover:bg-blue-400 shadow-blue-500/25'
    : 'bg-emerald-500 hover:bg-emerald-400 shadow-emerald-500/25';

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

      // Store tokens and metadata
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('account_type', accountType);
      }

      // Direct to corresponding dashboard
      if (accountType === 'individual') {
        router.push('/individual/dashboard');
      } else {
        router.push('/enterprise/dashboard');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'An error occurred during registration.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-black flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-zinc-100 relative overflow-hidden">
      {/* Ambient background glow, consistent with the rest of the app */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="w-[600px] h-[600px] bg-red-600/[0.08] blur-[150px] animate-aurora rounded-full absolute -top-40 left-1/2 -translate-x-1/2" />
        <div className={`w-[500px] h-[500px] ${isIndividual ? 'bg-blue-600/[0.06]' : 'bg-emerald-600/[0.06]'} blur-[140px] animate-aurora-red rounded-full absolute bottom-0 -right-20 transition-colors duration-500`} />
      </div>

      <div className="relative z-10 sm:mx-auto sm:w-full sm:max-w-md">
        <Link href="/" className="flex items-center justify-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-white/90 via-white/70 to-white/40 flex items-center justify-center text-black shadow-lg shadow-white/10 font-bold">
            <Sparkles className="w-4 h-4" />
          </div>
          <span className="text-xl font-bold tracking-tight text-white font-mono">EJICODE_AI</span>
        </Link>
        <h2 className="text-center text-2xl font-bold tracking-tight text-white">
          Create your workspace
        </h2>
        <p className="mt-2 text-center text-xs text-zinc-500">
          Choose your account type below &mdash; individual and enterprise workspaces are built differently.
        </p>
      </div>

      <div className="relative z-10 mt-6 sm:mx-auto sm:w-full sm:max-w-xl">
        <div className="apple-glass py-8 px-6 rounded-3xl sm:px-10">
          {/* Track Switcher */}
          <div className="grid grid-cols-2 gap-3 p-1 bg-black/40 rounded-xl border border-white/10 mb-6">
            <button
              type="button"
              onClick={() => setAccountType('individual')}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                isIndividual
                  ? 'bg-blue-500 text-white shadow-sm'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              <Users className="w-4 h-4" />
              Individual
            </button>
            <button
              type="button"
              onClick={() => setAccountType('enterprise')}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                !isIndividual
                  ? 'bg-emerald-500 text-white shadow-sm'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              <Building2 className="w-4 h-4" />
              Enterprise
            </button>
          </div>

          {errorMsg && (
            <div className="mb-6 p-4 rounded-xl bg-red-950/40 border border-red-500/30 flex items-start gap-3 text-red-200 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0 text-red-400 mt-0.5" />
              <div>{errorMsg}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Common Fields */}
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                Full Name
              </label>
              <div className="relative">
                <User className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Jane Doe"
                  className={`w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none ${accentBorder}`}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                {isIndividual ? 'Email Address' : 'Work Email Address'}
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={isIndividual ? 'jane@gmail.com' : 'jane@acmecorp.com'}
                  className={`w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none ${accentBorder}`}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                <input
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className={`w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none ${accentBorder}`}
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
                    <Briefcase className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="e.g. Senior AI Platform Engineer"
                      className={`w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none ${accentBorder}`}
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
                    className={`w-full px-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none ${accentBorder}`}
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                      Location
                    </label>
                    <div className="relative">
                      <MapPin className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                      <input
                        type="text"
                        value={location}
                        onChange={(e) => setLocation(e.target.value)}
                        placeholder="Remote or City"
                        className={`w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none ${accentBorder}`}
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
                      className={`w-full px-3 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none ${accentBorder}`}
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
                    <Building2 className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                    <input
                      type="text"
                      required
                      value={orgName}
                      onChange={(e) => setOrgName(e.target.value)}
                      placeholder="e.g. Acme Technologies Inc."
                      className={`w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none ${accentBorder}`}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                      Company Domain
                    </label>
                    <div className="relative">
                      <Globe className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                      <input
                        type="text"
                        value={domain}
                        onChange={(e) => setDomain(e.target.value)}
                        placeholder="acmecorp.com"
                        className={`w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none ${accentBorder}`}
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
                      className={`w-full px-3 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none ${accentBorder}`}
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
              className={`w-full mt-4 py-3 px-4 font-semibold text-white rounded-full transition-all shadow-md flex items-center justify-center gap-2 ${accentButton} disabled:opacity-50`}
            >
              <ShieldCheck className="w-4 h-4" />
              <span>
                {isSubmitting
                  ? 'Creating Workspace…'
                  : isIndividual
                  ? 'Create Individual Account'
                  : 'Create Enterprise Account'}
              </span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-white/10 text-center text-xs text-zinc-500">
            Already have an account?{' '}
            <Link href="/login" className={`${accentText} hover:underline font-semibold`}>
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-black flex items-center justify-center text-zinc-500 text-sm">Loading workspace setup...</div>}>
      <RegisterContent />
    </Suspense>
  );
}
