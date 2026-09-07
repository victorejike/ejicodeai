'use client';

import { useState, useEffect, FormEvent, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Sparkles,
  Lock,
  Mail,
  User,
  ArrowRight,
  ShieldCheck,
  Building2,
  Users,
  AlertCircle,
  Github,
  KeyRound,
} from 'lucide-react';
import { resolvePostLoginDestination } from '@/lib/onboarding';

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [accountTypeHint, setAccountTypeHint] = useState<'individual' | 'enterprise'>(
    searchParams.get('type') === 'enterprise' ? 'enterprise' : 'individual'
  );
  const [error, setError] = useState(searchParams.get('error') || '');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(false);
  const [githubLoading, setGithubLoading] = useState(false);

  useEffect(() => {
    const typeParam = searchParams.get('type');
    if (typeParam === 'enterprise' || typeParam === 'individual') {
      setAccountTypeHint(typeParam);
    }
  }, [searchParams]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setNotice('');
    setLoading(true);

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.error || 'Invalid credentials. Please check your username/email and password.');
        return;
      }

      // Store credentials and session metadata
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
      }
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token);
      }

      const userAccountType = data.user?.account_type || accountTypeHint;
      localStorage.setItem('account_type', userAccountType);
      if (data.user) {
        localStorage.setItem('user', JSON.stringify(data.user));
      }

      // Route to the profile/knowledge-base setup step first if onboarding isn't
      // complete yet - discovery has nothing real to work from until then.
      const destination = await resolvePostLoginDestination(userAccountType, data.access_token);
      router.push(destination);
      router.refresh();
    } catch {
      setError('Network error — please check if the server is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleGitHubLogin = async () => {
    setGithubLoading(true);
    setError('');
    setNotice('');

    try {
      const res = await fetch(`/api/auth/github?type=${accountTypeHint}`);
      const data = await res.json();

      if (data.status === 'not_configured') {
        setNotice(
          'GitHub OAuth is ready in code, but GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET are not yet set in .env. You can sign in immediately using Email/Password below!'
        );
      } else if (data.url) {
        window.location.href = data.url;
      }
    } catch {
      setError('Could not connect to GitHub OAuth service.');
    } finally {
      setGithubLoading(false);
    }
  };

  const fillQuickDemo = (type: 'individual' | 'enterprise') => {
    setAccountTypeHint(type);
    setUsername('admin');
    setPassword('admin');
    setError('');
    setNotice(`Loaded demo admin credentials for ${type === 'individual' ? 'Individual' : 'Enterprise'} context.`);
  };

  const isIndividual = accountTypeHint === 'individual';
  const accentText = isIndividual ? 'text-blue-400' : 'text-emerald-400';
  const accentBorder = isIndividual ? 'focus:border-blue-400/50' : 'focus:border-emerald-400/50';
  const accentButton = isIndividual
    ? 'bg-blue-500 hover:bg-blue-400 shadow-blue-500/25'
    : 'bg-emerald-500 hover:bg-emerald-400 shadow-emerald-500/25';

  return (
    <div className="min-h-screen bg-black flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-zinc-100 relative overflow-hidden">
      {/* Ambient background glow, consistent with the rest of the app */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="w-[600px] h-[600px] bg-red-600/[0.08] blur-[150px] animate-aurora rounded-full absolute -top-40 left-1/2 -translate-x-1/2" />
        <div className={`w-[500px] h-[500px] ${isIndividual ? 'bg-blue-600/[0.06]' : 'bg-emerald-600/[0.06]'} blur-[140px] animate-aurora-red rounded-full absolute bottom-0 -right-20 transition-colors duration-500`} />
      </div>

      <div className="relative z-10 sm:mx-auto sm:w-full sm:max-w-md">
        {/* Logo */}
        <Link href="/" className="flex items-center justify-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-white/90 via-white/70 to-white/40 flex items-center justify-center text-black shadow-lg shadow-white/10 font-bold">
            <Sparkles className="w-4 h-4" />
          </div>
          <span className="text-xl font-bold tracking-tight text-white font-mono">EJICODE_AI</span>
        </Link>
        <h2 className="text-center text-2xl font-bold tracking-tight text-white">
          Sign in to your workspace
        </h2>
        <p className="mt-2 text-center text-xs text-zinc-500">
          One AI platform &bull; two sides of hiring &bull; zero fabricated data
        </p>
      </div>

      <div className="relative z-10 mt-6 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="apple-glass py-8 px-6 rounded-3xl sm:px-10">
          {/* Account Track Switcher */}
          <div className="grid grid-cols-2 gap-2 p-1 bg-black/40 rounded-xl border border-white/10 mb-6">
            <button
              type="button"
              onClick={() => setAccountTypeHint('individual')}
              className={`flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-medium transition-all ${
                isIndividual
                  ? 'bg-blue-500 text-white shadow-sm font-semibold'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              Individual
            </button>
            <button
              type="button"
              onClick={() => setAccountTypeHint('enterprise')}
              className={`flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-medium transition-all ${
                !isIndividual
                  ? 'bg-emerald-500 text-white shadow-sm font-semibold'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              <Building2 className="w-3.5 h-3.5" />
              Enterprise
            </button>
          </div>

          {/* GitHub OAuth Button */}
          <button
            type="button"
            onClick={handleGitHubLogin}
            disabled={githubLoading}
            className="apple-button-secondary w-full mb-5 py-2.5 px-4 text-xs font-semibold flex items-center justify-center gap-2.5 disabled:opacity-50"
          >
            <Github className="w-4 h-4" />
            <span>{githubLoading ? 'Connecting to GitHub...' : 'Continue with GitHub'}</span>
          </button>

          <div className="relative flex py-2 items-center mb-5">
            <div className="flex-grow border-t border-white/10"></div>
            <span className="flex-shrink mx-3 text-[11px] text-zinc-500 uppercase font-mono tracking-wider">
              Or sign in with email
            </span>
            <div className="flex-grow border-t border-white/10"></div>
          </div>

          {error && (
            <div className="mb-4 p-3.5 rounded-xl bg-red-950/40 border border-red-500/30 flex items-start gap-2.5 text-red-200 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-400 mt-0.5" />
              <div>{error}</div>
            </div>
          )}

          {notice && (
            <div className="mb-4 p-3.5 rounded-xl bg-blue-950/40 border border-blue-500/30 flex items-start gap-2.5 text-blue-200 text-xs">
              <Sparkles className="w-4 h-4 shrink-0 text-blue-400 mt-0.5" />
              <div>{notice}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                {isIndividual ? 'Email or Username' : 'Work Email or Org Username'}
              </label>
              <div className="relative">
                <User className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder={isIndividual ? 'e.g. jane@example.com or admin' : 'e.g. talent@acme.com or admin'}
                  className={`w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none ${accentBorder} transition-colors`}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-medium text-zinc-300">Password</label>
                <Link
                  href="/forgot-password"
                  className={`text-xs ${accentText} hover:underline transition-colors flex items-center gap-1`}
                >
                  <KeyRound className="w-3 h-3" />
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className={`w-full pl-9 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm focus:outline-none ${accentBorder} transition-colors`}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className={`w-full py-2.5 px-4 font-semibold text-white rounded-full transition-all shadow-md flex items-center justify-center gap-2 ${accentButton} disabled:opacity-50 text-sm`}
            >
              <ShieldCheck className="w-4 h-4" />
              <span>
                {loading
                  ? 'Authenticating…'
                  : isIndividual
                  ? 'Sign in as Individual'
                  : 'Sign in as Enterprise'}
              </span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Demo Credentials */}
          <div className="mt-5 p-3 rounded-xl bg-black/40 border border-white/10 text-[11px] text-zinc-500">
            <div className="flex items-center justify-between">
              <span>Local Dev Quick Fill:</span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => fillQuickDemo('individual')}
                  className="text-blue-400 hover:underline font-mono"
                >
                  Individual
                </button>
                <span>&bull;</span>
                <button
                  type="button"
                  onClick={() => fillQuickDemo('enterprise')}
                  className="text-emerald-400 hover:underline font-mono"
                >
                  Enterprise
                </button>
              </div>
            </div>
          </div>

          {/* Registration Links */}
          <div className="mt-6 pt-4 border-t border-white/10 space-y-2 text-center text-xs text-zinc-500">
            <div>
              Don&apos;t have an account?
            </div>
            <div className="flex items-center justify-center gap-3">
              <Link
                href="/register?type=individual"
                className="text-blue-400 hover:text-blue-300 hover:underline font-semibold flex items-center gap-1"
              >
                <Users className="w-3 h-3" />
                Join as Individual
              </Link>
              <span>&bull;</span>
              <Link
                href="/register?type=enterprise"
                className="text-emerald-400 hover:text-emerald-300 hover:underline font-semibold flex items-center gap-1"
              >
                <Building2 className="w-3 h-3" />
                Register Enterprise
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-black flex items-center justify-center text-xs text-zinc-500">Loading sign in...</div>}>
      <LoginContent />
    </Suspense>
  );
}
