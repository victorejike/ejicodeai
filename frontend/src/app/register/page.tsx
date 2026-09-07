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
    <div className="min-h-screen bg-[#0d1117] flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-[#e6edf3]">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Link href="/" className="flex items-center justify-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#1f6feb] to-[#a371f7] flex items-center justify-center text-white shadow-lg shadow-[#1f6feb]/20 font-bold">
            <Sparkles className="w-5 h-5" />
          </div>
          <span className="text-xl font-bold tracking-tight text-white">EJICODE AI</span>
        </Link>
        <h2 className="text-center text-2xl font-bold tracking-tight text-white">
          Create your platform account
        </h2>
        <p className="mt-2 text-center text-xs text-[#8b949e]">
          Choose your workspace type below to begin your autonomous BD journey.
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-xl">
        <div className="bg-[#161b22] py-8 px-6 shadow-2xl border border-[#30363d] rounded-2xl sm:px-10">
          {/* Track Switcher */}
          <div className="grid grid-cols-2 gap-3 p-1 bg-[#0d1117] rounded-xl border border-[#30363d] mb-6">
            <button
              type="button"
              onClick={() => setAccountType('individual')}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                accountType === 'individual'
                  ? 'bg-[#1f6feb] text-white shadow-sm'
                  : 'text-[#8b949e] hover:text-white'
              }`}
            >
              <Users className="w-4 h-4" />
              Individual Candidate
            </button>
            <button
              type="button"
              onClick={() => setAccountType('enterprise')}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                accountType === 'enterprise'
                  ? 'bg-[#238636] text-white shadow-sm'
                  : 'text-[#8b949e] hover:text-white'
              }`}
            >
              <Building2 className="w-4 h-4" />
              Enterprise Talent
            </button>
          </div>

          {errorMsg && (
            <div className="mb-6 p-4 rounded-xl bg-red-900/30 border border-red-700/50 flex items-start gap-3 text-red-200 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0 text-red-400 mt-0.5" />
              <div>{errorMsg}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Common Fields */}
            <div>
              <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                Full Name
              </label>
              <div className="relative">
                <User className="w-4 h-4 absolute left-3 top-3 text-[#8b949e]" />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Jane Doe"
                  className="w-full pl-9 pr-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-sm focus:outline-none focus:border-[#1f6feb]"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                {accountType === 'individual' ? 'Email Address' : 'Work Email Address'}
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 absolute left-3 top-3 text-[#8b949e]" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={accountType === 'individual' ? 'jane@gmail.com' : 'jane@acmecorp.com'}
                  className="w-full pl-9 pr-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-sm focus:outline-none focus:border-[#1f6feb]"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 absolute left-3 top-3 text-[#8b949e]" />
                <input
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-sm focus:outline-none focus:border-[#1f6feb]"
                />
              </div>
            </div>

            {/* Individual Candidate Fields */}
            {accountType === 'individual' && (
              <>
                <div>
                  <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                    Target Role / Headline
                  </label>
                  <div className="relative">
                    <Briefcase className="w-4 h-4 absolute left-3 top-3 text-[#8b949e]" />
                    <input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="e.g. Senior AI Platform Engineer"
                      className="w-full pl-9 pr-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-sm focus:outline-none focus:border-[#1f6feb]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                    Primary Skills (Comma-separated)
                  </label>
                  <input
                    type="text"
                    value={skillsStr}
                    onChange={(e) => setSkillsStr(e.target.value)}
                    placeholder="Python, FastAPI, React, Docker, Kubernetes"
                    className="w-full px-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-sm focus:outline-none focus:border-[#1f6feb]"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                      Location
                    </label>
                    <div className="relative">
                      <MapPin className="w-4 h-4 absolute left-3 top-3 text-[#8b949e]" />
                      <input
                        type="text"
                        value={location}
                        onChange={(e) => setLocation(e.target.value)}
                        placeholder="Remote or City"
                        className="w-full pl-9 pr-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-sm focus:outline-none focus:border-[#1f6feb]"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                      Preference
                    </label>
                    <select
                      value={remotePreference}
                      onChange={(e) => setRemotePreference(e.target.value)}
                      className="w-full px-3 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-sm focus:outline-none focus:border-[#1f6feb]"
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

            {/* Enterprise Specific Fields */}
            {accountType === 'enterprise' && (
              <>
                <div>
                  <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                    Organization / Company Name
                  </label>
                  <div className="relative">
                    <Building2 className="w-4 h-4 absolute left-3 top-3 text-[#8b949e]" />
                    <input
                      type="text"
                      required
                      value={orgName}
                      onChange={(e) => setOrgName(e.target.value)}
                      placeholder="e.g. Acme Technologies Inc."
                      className="w-full pl-9 pr-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-sm focus:outline-none focus:border-[#1f6feb]"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                      Company Domain
                    </label>
                    <div className="relative">
                      <Globe className="w-4 h-4 absolute left-3 top-3 text-[#8b949e]" />
                      <input
                        type="text"
                        value={domain}
                        onChange={(e) => setDomain(e.target.value)}
                        placeholder="acmecorp.com"
                        className="w-full pl-9 pr-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-sm focus:outline-none focus:border-[#1f6feb]"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                      Plan Tier
                    </label>
                    <select
                      value={planTier}
                      onChange={(e) => setPlanTier(e.target.value)}
                      className="w-full px-3 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-sm focus:outline-none focus:border-[#1f6feb]"
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
              className={`w-full mt-4 py-3 px-4 font-semibold text-white rounded-xl transition-all shadow-md flex items-center justify-center gap-2 ${
                accountType === 'individual'
                  ? 'bg-[#1f6feb] hover:bg-[#388bfd] shadow-[#1f6feb]/25'
                  : 'bg-[#238636] hover:bg-[#2ea043] shadow-[#238636]/25'
              } disabled:opacity-50`}
            >
              <ShieldCheck className="w-4 h-4" />
              <span>
                {isSubmitting
                  ? 'Creating Workspace…'
                  : accountType === 'individual'
                  ? 'Launch Candidate Profile'
                  : 'Initialize Enterprise Pipeline'}
              </span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-[#30363d] text-center text-xs text-[#8b949e]">
            Already have an account?{' '}
            <Link href="/login" className="text-[#58a6ff] hover:underline font-semibold">
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
    <Suspense fallback={<div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400 text-sm">Loading workspace setup...</div>}>
      <RegisterContent />
    </Suspense>
  );
}
