'use client';

import { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  KeyRound,
  Mail,
  ShieldCheck,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Lock,
  RefreshCw,
  Sparkles,
  AlertCircle,
  Eye,
} from 'lucide-react';

function ForgotPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // 8-step flow state:
  // Step 1: 'email_input'
  // Step 2: 'request_dispatching'
  // Step 3: 'email_sent_confirmation'
  // Step 4: 'token_input'
  // Step 5: 'token_verifying'
  // Step 6: 'new_password_input'
  // Step 7: 'password_resetting'
  // Step 8: 'success_complete'
  const [step, setStep] = useState<number>(1);
  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [devTokenNotice, setDevTokenNotice] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);

  useEffect(() => {
    const urlToken = searchParams.get('token');
    if (urlToken) {
      setToken(urlToken);
      setStep(4);
    }
  }, [searchParams]);

  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown((prev) => prev - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const getPasswordStrength = (pass: string) => {
    let score = 0;
    if (pass.length >= 8) score += 25;
    if (/[A-Z]/.test(pass)) score += 25;
    if (/[0-9]/.test(pass)) score += 25;
    if (/[^A-Za-z0-9]/.test(pass)) score += 25;
    return score;
  };

  const strength = getPasswordStrength(newPassword);

  const handleRequestToken = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);
    setStep(2);

    try {
      const res = await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, action: 'request' }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Request failed');
      }

      if (data.dev_reset_token) {
        setDevTokenNotice(data.dev_reset_token);
      }

      setResendCooldown(60);
      setStep(3);
    } catch (err: any) {
      setErrorMsg(err.message || 'Unable to request password reset');
      setStep(1);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifyToken = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);
    setStep(5);

    try {
      const res = await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token.trim(), action: 'verify' }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Invalid or expired token');
      }

      setStep(6);
    } catch (err: any) {
      setErrorMsg(err.message || 'Token verification failed. Please try again.');
      setStep(4);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setErrorMsg('Passwords do not match');
      return;
    }
    if (newPassword.length < 8) {
      setErrorMsg('Password must be at least 8 characters long');
      return;
    }

    setErrorMsg(null);
    setIsSubmitting(true);
    setStep(7);

    try {
      const res = await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: token.trim(),
          new_password: newPassword,
          action: 'reset',
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Password reset failed');
      }

      setStep(8);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to reset password');
      setStep(6);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#000000] text-[#f4f4f5] selection:bg-white selection:text-black relative overflow-x-hidden font-sans flex flex-col justify-between">
      {/* Ambient background glow */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="w-[800px] h-[800px] bg-red-600/[0.10] blur-[160px] animate-aurora rounded-full absolute -top-40 left-1/4" />
        <div className="w-[650px] h-[650px] bg-blue-600/[0.06] blur-[150px] animate-aurora-red rounded-full absolute top-1/3 -right-40" />
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

      {/* Main Container */}
      <main className="relative z-10 flex-1 flex flex-col justify-center items-center pt-32 pb-12 px-4 sm:px-6 lg:px-8">
        <div className="w-full max-w-md mx-auto text-center mb-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full apple-glass-subtle text-xs text-zinc-300 font-medium mb-3 animate-float">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span>Cryptographic Security Recovery</span>
          </div>

          <h1 className="text-3xl font-semibold tracking-tight text-white leading-tight">
            Account <span className="text-gradient-apple-glow font-bold">Recovery</span>
          </h1>

          {/* 8-Step Progress Indicator */}
          <div className="mt-4 px-2">
            <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500 mb-1.5">
              <span>Security Recovery</span>
              <span className="text-red-400 font-semibold">Step {step} of 8</span>
            </div>
            <div className="w-full bg-white/10 h-1 rounded-full overflow-hidden">
              <div
                className="bg-gradient-to-r from-red-500 to-white h-full transition-all duration-300 rounded-full"
                style={{ width: `${(step / 8) * 100}%` }}
              />
            </div>
          </div>
        </div>

        <div className="w-full max-w-md mx-auto">
          <div className="apple-glass p-6 sm:p-8 rounded-3xl shadow-2xl border border-white/10 relative overflow-hidden backdrop-blur-3xl">
            {errorMsg && (
              <div className="mb-6 p-3.5 rounded-2xl bg-red-950/40 border border-red-500/30 flex items-start gap-3 text-red-200 text-xs">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-400 mt-0.5" />
                <div>{errorMsg}</div>
              </div>
            )}

            {/* STEP 1: Enter Email */}
            {step === 1 && (
              <div>
                <div className="text-center mb-5">
                  <h2 className="text-xl font-bold text-white">Reset your password</h2>
                  <p className="text-xs text-zinc-400 mt-1.5 leading-relaxed">
                    Enter your verified account email to receive a single-use cryptographic recovery token.
                  </p>
                </div>

                <form onSubmit={handleRequestToken} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                      Account Email Address
                    </label>
                    <div className="relative">
                      <Mail className="w-4 h-4 absolute left-3.5 top-3 text-zinc-500" />
                      <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="name@company.com"
                        className="w-full pl-10 pr-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-red-400/60 focus:ring-1 focus:ring-red-400/30 transition-all"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmitting || !email}
                    className="apple-button-primary w-full mt-2 py-3 px-4 disabled:opacity-50 flex items-center justify-center gap-2 text-xs font-semibold"
                  >
                    <span>Send Recovery Token</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </form>
              </div>
            )}

            {/* STEP 2: Dispatching animation */}
            {step === 2 && (
              <div className="text-center py-8 space-y-4">
                <div className="w-14 h-14 rounded-full bg-white/10 border border-white/20 flex items-center justify-center mx-auto text-white animate-pulse">
                  <RefreshCw className="w-6 h-6 animate-spin" />
                </div>
                <h3 className="text-base font-bold text-white">Dispatching Recovery Instructions…</h3>
                <p className="text-xs text-zinc-500">
                  Encrypting single-use cryptographic token with SHA-256 ledger check.
                </p>
              </div>
            )}

            {/* STEP 3: Email sent confirmation */}
            {step === 3 && (
              <div className="text-center py-4 space-y-4">
                <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-400/30 flex items-center justify-center mx-auto text-emerald-400">
                  <Mail className="w-7 h-7" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Recovery token dispatched</h3>
                  <p className="text-xs text-zinc-400 mt-1.5">
                    If an account exists for <span className="text-white font-medium">{email}</span>, a secure recovery code has been generated.
                  </p>
                </div>

                {devTokenNotice && (
                  <div className="p-3 bg-black/50 rounded-2xl border border-white/10 text-left">
                    <div className="text-[10px] font-mono uppercase text-amber-400 font-semibold flex items-center gap-1.5 mb-1">
                      <Sparkles className="w-3 h-3" />
                      <span>Sandbox Dev Token:</span>
                    </div>
                    <div className="text-xs font-mono text-red-300 break-all select-all bg-white/5 p-2 rounded-xl">
                      {devTokenNotice}
                    </div>
                  </div>
                )}

                <button
                  onClick={() => {
                    if (devTokenNotice) setToken(devTokenNotice);
                    setStep(4);
                  }}
                  className="apple-button-primary w-full py-3 px-4 flex items-center justify-center gap-2 text-xs font-semibold"
                >
                  <span>Enter Recovery Token</span>
                  <ArrowRight className="w-4 h-4" />
                </button>

                <div className="text-xs text-zinc-500">
                  Didn&apos;t receive it?{' '}
                  <button
                    disabled={resendCooldown > 0}
                    onClick={handleRequestToken}
                    className="text-red-400 hover:text-red-300 hover:underline disabled:opacity-50"
                  >
                    Resend code {resendCooldown > 0 ? `(${resendCooldown}s)` : ''}
                  </button>
                </div>
              </div>
            )}

            {/* STEP 4: Token input */}
            {step === 4 && (
              <div>
                <div className="text-center mb-5">
                  <h2 className="text-xl font-bold text-white">Verify Recovery Token</h2>
                  <p className="text-xs text-zinc-500 mt-1">
                    Paste the 64-character verification code delivered to your email.
                  </p>
                </div>

                <form onSubmit={handleVerifyToken} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                      Security Token
                    </label>
                    <div className="relative">
                      <KeyRound className="w-4 h-4 absolute left-3.5 top-3 text-zinc-500" />
                      <input
                        type="text"
                        required
                        value={token}
                        onChange={(e) => setToken(e.target.value)}
                        placeholder="Paste cryptographic token"
                        className="w-full pl-10 pr-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white font-mono text-xs focus:outline-none focus:border-red-400/60 focus:ring-1 focus:ring-red-400/30"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmitting || token.length < 8}
                    className="apple-button-primary w-full py-3 px-4 disabled:opacity-50 flex items-center justify-center gap-2 text-xs font-semibold"
                  >
                    <span>Verify Token</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>

                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="w-full text-xs text-zinc-500 hover:text-white transition-colors"
                  >
                    ← Request a different email
                  </button>
                </form>
              </div>
            )}

            {/* STEP 5: Token verifying animation */}
            {step === 5 && (
              <div className="text-center py-8 space-y-4">
                <div className="w-14 h-14 rounded-full bg-white/10 border border-white/20 flex items-center justify-center mx-auto text-white">
                  <RefreshCw className="w-6 h-6 animate-spin" />
                </div>
                <h3 className="text-base font-bold text-white">Verifying Token Signature…</h3>
                <p className="text-xs text-zinc-500">
                  Validating cryptographic token hash against database ledger.
                </p>
              </div>
            )}

            {/* STEP 6: Enter new password */}
            {step === 6 && (
              <div>
                <div className="text-center mb-5">
                  <h2 className="text-xl font-bold text-white">Create New Password</h2>
                  <p className="text-xs text-zinc-500 mt-1">
                    Choose a strong, unique password for your account.
                  </p>
                </div>

                <form onSubmit={handleResetPassword} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                      New Password
                    </label>
                    <div className="relative">
                      <Lock className="w-4 h-4 absolute left-3.5 top-3 text-zinc-500" />
                      <input
                        type="password"
                        required
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full pl-10 pr-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-red-400/60"
                      />
                    </div>

                    {/* Password Strength Meter */}
                    <div className="mt-2 space-y-1">
                      <div className="flex justify-between text-[11px] text-zinc-500 font-mono">
                        <span>Strength</span>
                        <span className={strength >= 75 ? 'text-emerald-400' : strength >= 50 ? 'text-amber-400' : 'text-red-400'}>
                          {strength >= 75 ? 'Strong' : strength >= 50 ? 'Medium' : 'Weak'}
                        </span>
                      </div>
                      <div className="w-full bg-white/10 h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-300 rounded-full ${
                            strength >= 75 ? 'bg-emerald-500' : strength >= 50 ? 'bg-amber-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${strength}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                      Confirm New Password
                    </label>
                    <div className="relative">
                      <Lock className="w-4 h-4 absolute left-3.5 top-3 text-zinc-500" />
                      <input
                        type="password"
                        required
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full pl-10 pr-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-red-400/60"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmitting || strength < 50 || newPassword !== confirmPassword}
                    className="apple-button-primary w-full py-3 px-4 disabled:opacity-50 flex items-center justify-center gap-2 text-xs font-semibold"
                  >
                    <ShieldCheck className="w-4 h-4" />
                    <span>Update Password</span>
                  </button>
                </form>
              </div>
            )}

            {/* STEP 7: Resetting animation */}
            {step === 7 && (
              <div className="text-center py-8 space-y-4">
                <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-400/30 flex items-center justify-center mx-auto text-emerald-400">
                  <RefreshCw className="w-6 h-6 animate-spin" />
                </div>
                <h3 className="text-base font-bold text-white">Updating Credentials…</h3>
                <p className="text-xs text-zinc-500">
                  Invalidating sessions and updating bcrypt cryptographic hash.
                </p>
              </div>
            )}

            {/* STEP 8: Success Complete */}
            {step === 8 && (
              <div className="text-center py-4 space-y-4">
                <div className="w-16 h-16 rounded-full bg-emerald-500/15 border border-emerald-400/40 flex items-center justify-center mx-auto text-emerald-400 shadow-lg shadow-emerald-500/10">
                  <CheckCircle2 className="w-8 h-8" />
                </div>
                <div>
                  <h3 className="text-xl font-extrabold text-white">Password Reset Successful!</h3>
                  <p className="text-xs text-zinc-400 mt-1.5">
                    Your credentials have been securely updated. You can now sign in to your workspace.
                  </p>
                </div>

                <Link
                  href="/login"
                  className="apple-button-primary w-full py-3 px-4 flex items-center justify-center gap-2 text-xs font-semibold"
                >
                  <span>Proceed to Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            )}

            <div className="mt-6 pt-4 border-t border-white/10 text-center">
              <Link href="/login" className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-white transition-colors">
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Sign In</span>
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
            <Link href="/register" className="hover:text-white transition-colors">Sign Up</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function ForgotPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-black flex items-center justify-center text-zinc-500 text-xs">Loading recovery portal...</div>}>
      <ForgotPasswordContent />
    </Suspense>
  );
}
