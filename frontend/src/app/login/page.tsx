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
  CheckCircle2,
  Eye,
  Bot,
  Layers,
  ArrowLeft,
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
          'GitHub OAuth is ready in code, but GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET are not configured in .env. You can sign in immediately using Email/Password below!'
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
    setNotice(`Loaded demo admin credentials for ${type === 'individual' ? 'Individual' : 'Enterprise'} track.`);
  };

  const isIndividual = accountTypeHint === 'individual';
  const trackAccentColor = isIndividual ? 'text-blue-400' : 'text-emerald-400';
  const trackGlowColor = isIndividual ? 'bg-blue-600/[0.08]' : 'bg-emerald-600/[0.08]';
  const trackBorder = isIndividual
    ? 'focus:border-blue-400/70 focus:ring-1 focus:ring-blue-400/30'
    : 'focus:border-emerald-400/70 focus:ring-1 focus:ring-emerald-400/30';

  return (
    <div className="min-h-screen bg-[#000000] text-[#f4f4f5] selection:bg-white selection:text-black relative overflow-x-hidden font-sans flex flex-col justify-between">
      {/* Dynamic Ambient Background Glows matching the AI landing page */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="w-[800px] h-[800px] bg-red-600/[0.10] blur-[160px] animate-aurora rounded-full absolute -top-40 left-1/4" />
        <div className={`w-[650px] h-[650px] ${trackGlowColor} blur-[150px] animate-aurora-red rounded-full absolute top-1/3 -right-40 transition-colors duration-700`} />
        <div className="w-[500px] h-[500px] bg-emerald-600/[0.04] blur-[140px] animate-aurora rounded-full absolute -bottom-20 left-10" />
      </div>

      {/* Floating Apple-Glass Header Pill matching the AI landing page */}
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
            <Link href="/#how-it-works" className="hover:text-white transition-colors">How it works</Link>
            <Link href="/#trust" className="hover:text-white transition-colors">Trust &amp; Data</Link>
          </nav>

          <div className="flex items-center gap-2 shrink-0">
            <Link
              href="/register"
              className="apple-button-secondary px-3.5 py-1.5 text-xs font-semibold whitespace-nowrap"
            >
              Join Platform
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content Container */}
      <main className="relative z-10 flex-1 flex flex-col justify-center items-center pt-32 pb-12 px-4 sm:px-6 lg:px-8">
        <div className="w-full max-w-md mx-auto text-center mb-7">
          {/* Floating AI Status Pill */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full apple-glass-subtle text-xs text-zinc-300 font-medium mb-4 animate-float">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span>Autonomous Career Agents &bull; Two Sides of Hiring</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-white leading-tight">
            Sign in to <span className="text-gradient-apple-glow font-bold">EJICODE AI</span>
          </h1>
          <p className="mt-2 text-xs sm:text-sm text-zinc-400 max-w-xs sm:max-w-sm mx-auto leading-relaxed">
            Autonomous multi-agent workflow for career advancement and enterprise hiring. Zero fabricated data.
          </p>
        </div>

        {/* Apple-Glass Bento Sign-In Card */}
        <div className="w-full max-w-md mx-auto">
          <div className="apple-glass p-6 sm:p-8 rounded-3xl shadow-2xl border border-white/10 relative overflow-hidden backdrop-blur-3xl">
            {/* Ambient accent inside card */}
            <div
              className={`absolute top-0 right-0 w-44 h-44 ${
                isIndividual ? 'bg-blue-600/10' : 'bg-emerald-600/10'
              } blur-[50px] pointer-events-none rounded-full transition-colors duration-500`}
            />

            {/* Dual Track Switcher (Individual vs Enterprise) */}
            <div className="grid grid-cols-2 gap-1.5 p-1 bg-black/50 rounded-2xl border border-white/10 mb-6">
              <button
                type="button"
                onClick={() => setAccountTypeHint('individual')}
                className={`flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isIndividual
                    ? 'bg-blue-500 text-white shadow-md font-bold'
                    : 'text-zinc-400 hover:text-white'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                <span>Individual</span>
              </button>
              <button
                type="button"
                onClick={() => setAccountTypeHint('enterprise')}
                className={`flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  !isIndividual
                    ? 'bg-emerald-500 text-white shadow-md font-bold'
                    : 'text-zinc-400 hover:text-white'
                }`}
              >
                <Building2 className="w-3.5 h-3.5" />
                <span>Enterprise</span>
              </button>
            </div>

            {/* GitHub OAuth Button */}
            <button
              type="button"
              onClick={handleGitHubLogin}
              disabled={githubLoading}
              className="apple-button-secondary w-full py-2.5 px-4 text-xs font-semibold flex items-center justify-center gap-2.5 disabled:opacity-50 transition-all hover:scale-[1.01]"
            >
              <Github className="w-4 h-4" />
              <span>{githubLoading ? 'Connecting to GitHub...' : 'Continue with GitHub'}</span>
            </button>

            {/* Divider */}
            <div className="relative flex py-4 items-center">
              <div className="flex-grow border-t border-white/10"></div>
              <span className="flex-shrink mx-3 text-[10px] text-zinc-500 uppercase font-mono tracking-wider">
                Or sign in with email
              </span>
              <div className="flex-grow border-t border-white/10"></div>
            </div>

            {/* Error & Notice Banners */}
            {error && (
              <div className="mb-4 p-3.5 rounded-2xl bg-red-950/40 border border-red-500/30 flex items-start gap-2.5 text-red-200 text-xs">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-400 mt-0.5" />
                <div>{error}</div>
              </div>
            )}

            {notice && (
              <div className="mb-4 p-3.5 rounded-2xl bg-blue-950/40 border border-blue-500/30 flex items-start gap-2.5 text-blue-200 text-xs">
                <Sparkles className="w-4 h-4 shrink-0 text-blue-400 mt-0.5" />
                <div>{notice}</div>
              </div>
            )}

            {/* Sign-in Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                  {isIndividual ? 'Email or Username' : 'Work Email or Org Username'}
                </label>
                <div className="relative">
                  <User className="w-4 h-4 absolute left-3.5 top-3 text-zinc-500" />
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder={isIndividual ? 'e.g. jane@example.com or admin' : 'e.g. talent@acme.com or admin'}
                    className={`w-full pl-10 pr-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white text-sm placeholder-zinc-500 focus:outline-none ${trackBorder} transition-all`}
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-medium text-zinc-300">Password</label>
                  <Link
                    href="/forgot-password"
                    className={`text-xs ${trackAccentColor} hover:underline transition-colors flex items-center gap-1`}
                  >
                    <KeyRound className="w-3 h-3" />
                    <span>Forgot password?</span>
                  </Link>
                </div>
                <div className="relative">
                  <Lock className="w-4 h-4 absolute left-3.5 top-3 text-zinc-500" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className={`w-full pl-10 pr-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white text-sm placeholder-zinc-500 focus:outline-none ${trackBorder} transition-all`}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className={`w-full py-3 px-4 font-semibold text-black rounded-full transition-all duration-300 shadow-lg flex items-center justify-center gap-2 ${
                  isIndividual
                    ? 'bg-gradient-to-r from-blue-400 to-white hover:opacity-90'
                    : 'bg-gradient-to-r from-emerald-400 to-white hover:opacity-90'
                } disabled:opacity-50 text-xs sm:text-sm hover:scale-[1.01]`}
              >
                <ShieldCheck className="w-4 h-4" />
                <span>
                  {loading
                    ? 'Authenticating workspace…'
                    : isIndividual
                    ? 'Sign in as Individual'
                    : 'Sign in as Enterprise'}
                </span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>

            {/* Quick Demo Credentials Strip */}
            <div className="mt-5 p-3 rounded-2xl bg-black/40 border border-white/10 text-[11px] text-zinc-400">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] text-zinc-500 uppercase tracking-wider">Sandbox Demo Fill:</span>
                <div className="flex items-center gap-2 font-mono">
                  <button
                    type="button"
                    onClick={() => fillQuickDemo('individual')}
                    className="text-blue-400 hover:text-blue-300 hover:underline"
                  >
                    Individual
                  </button>
                  <span className="text-zinc-700">&bull;</span>
                  <button
                    type="button"
                    onClick={() => fillQuickDemo('enterprise')}
                    className="text-emerald-400 hover:text-emerald-300 hover:underline"
                  >
                    Enterprise
                  </button>
                </div>
              </div>
            </div>

            {/* Registration Direct Links */}
            <div className="mt-6 pt-4 border-t border-white/10 text-center text-xs text-zinc-500">
              <span>Don&apos;t have an account?</span>
              <div className="mt-2 flex items-center justify-center gap-3">
                <Link
                  href="/register?type=individual"
                  className="text-blue-400 hover:text-blue-300 hover:underline font-semibold flex items-center gap-1"
                >
                  <Users className="w-3.5 h-3.5" />
                  <span>Join as Individual</span>
                </Link>
                <span className="text-zinc-700">&bull;</span>
                <Link
                  href="/register?type=enterprise"
                  className="text-emerald-400 hover:text-emerald-300 hover:underline font-semibold flex items-center gap-1"
                >
                  <Building2 className="w-3.5 h-3.5" />
                  <span>Register Enterprise</span>
                </Link>
              </div>
            </div>
          </div>

          {/* Micro Trust Indicators below the card */}
          <div className="mt-6 grid grid-cols-3 gap-2 text-center text-[10px] text-zinc-500 font-mono">
            <div className="flex items-center justify-center gap-1 apple-glass-subtle py-1.5 px-2 rounded-xl">
              <ShieldCheck className="w-3 h-3 text-red-400 shrink-0" />
              <span className="truncate">Zero Fabricated Data</span>
            </div>
            <div className="flex items-center justify-center gap-1 apple-glass-subtle py-1.5 px-2 rounded-xl">
              <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
              <span className="truncate">6-Factor Evidence</span>
            </div>
            <div className="flex items-center justify-center gap-1 apple-glass-subtle py-1.5 px-2 rounded-xl">
              <Eye className="w-3 h-3 text-blue-400 shrink-0" />
              <span className="truncate">Human Approval Gate</span>
            </div>
          </div>
        </div>
      </main>

      {/* Sleek Minimal Footer */}
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
            <Link href="/register" className="hover:text-white transition-colors">Sign Up</Link>
            <Link href="/forgot-password" className="hover:text-white transition-colors">Forgot Password?</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-black flex items-center justify-center text-xs text-zinc-500">
          Loading sign in...
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
