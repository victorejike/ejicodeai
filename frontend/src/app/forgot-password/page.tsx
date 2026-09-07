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

  // Check URL query param for pre-filled token (e.g. ?token=...)
  useEffect(() => {
    const urlToken = searchParams.get('token');
    if (urlToken) {
      setToken(urlToken);
      setStep(4); // Advance to token verification
    }
  }, [searchParams]);

  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown((prev) => prev - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  // Password strength calculation
  const getPasswordStrength = (pass: string) => {
    let score = 0;
    if (pass.length >= 8) score += 25;
    if (/[A-Z]/.test(pass)) score += 25;
    if (/[0-9]/.test(pass)) score += 25;
    if (/[^A-Za-z0-9]/.test(pass)) score += 25;
    return score;
  };

  const strength = getPasswordStrength(newPassword);

  // Step 1 & 2 -> 3: Request reset token
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
      setStep(3); // Email sent confirmation
    } catch (err: any) {
      setErrorMsg(err.message || 'Unable to request password reset');
      setStep(1);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Step 4 & 5 -> 6: Verify token
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

      setStep(6); // New password entry
    } catch (err: any) {
      setErrorMsg(err.message || 'Token verification failed. Please try again.');
      setStep(4);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Step 6 & 7 -> 8: Set new password
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

      setStep(8); // Success
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to reset password');
      setStep(6);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0d1117] flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-[#e6edf3]">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Link href="/" className="flex items-center justify-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#1f6feb] to-[#a371f7] flex items-center justify-center text-white shadow-lg shadow-[#1f6feb]/20 font-bold">
            <Lock className="w-5 h-5" />
          </div>
          <span className="text-xl font-bold tracking-tight text-white">EJICODE AI</span>
        </Link>

        {/* 8-Step Progress Indicator */}
        <div className="mb-6 px-4">
          <div className="flex items-center justify-between text-xs font-mono text-[#8b949e] mb-2">
            <span>Security Recovery Flow</span>
            <span className="text-[#58a6ff] font-semibold">Step {step} of 8</span>
          </div>
          <div className="w-full bg-[#21262d] h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-gradient-to-r from-[#1f6feb] to-[#2ea043] h-full transition-all duration-300 rounded-full"
              style={{ width: `${(step / 8) * 100}%` }}
            ></div>
          </div>
        </div>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-[#161b22] py-8 px-6 shadow-2xl border border-[#30363d] rounded-2xl sm:px-10">
          {errorMsg && (
            <div className="mb-6 p-4 rounded-xl bg-red-900/30 border border-red-700/50 flex items-start gap-3 text-red-200 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0 text-red-400 mt-0.5" />
              <div>{errorMsg}</div>
            </div>
          )}

          {/* STEP 1: Enter Email */}
          {step === 1 && (
            <div>
              <div className="text-center mb-6">
                <h2 className="text-2xl font-bold text-white">Reset your password</h2>
                <p className="text-sm text-[#8b949e] mt-2">
                  Enter your verified account email address to receive a secure single-use recovery token.
                </p>
              </div>

              <form onSubmit={handleRequestToken} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                    Account Email Address
                  </label>
                  <div className="relative">
                    <Mail className="w-5 h-5 absolute left-3 top-2.5 text-[#8b949e]" />
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@company.com"
                      className="w-full pl-10 pr-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-sm focus:outline-none focus:border-[#1f6feb] transition-colors"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting || !email}
                  className="w-full mt-2 py-3 px-4 bg-[#1f6feb] hover:bg-[#388bfd] disabled:opacity-50 text-white font-semibold rounded-xl transition-all shadow-md shadow-[#1f6feb]/20 flex items-center justify-center gap-2"
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
              <div className="w-14 h-14 rounded-full bg-[#1f6feb]/15 border border-[#1f6feb]/40 flex items-center justify-center mx-auto text-[#58a6ff] animate-pulse">
                <RefreshCw className="w-6 h-6 animate-spin" />
              </div>
              <h3 className="text-lg font-bold text-white">Dispatching Recovery Instructions…</h3>
              <p className="text-xs text-[#8b949e]">
                Encrypting single-use cryptographic token with SHA-256 and verified expiration.
              </p>
            </div>
          )}

          {/* STEP 3: Email sent confirmation */}
          {step === 3 && (
            <div className="text-center py-4 space-y-5">
              <div className="w-14 h-14 rounded-full bg-[#238636]/15 border border-[#238636]/40 flex items-center justify-center mx-auto text-[#2ea043]">
                <Mail className="w-7 h-7" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-white">Recovery token dispatched</h3>
                <p className="text-sm text-[#8b949e] mt-2">
                  If an account exists for <span className="text-white font-medium">{email}</span>, a secure recovery code has been generated.
                </p>
              </div>

              {devTokenNotice && (
                <div className="p-3 bg-[#0d1117] rounded-xl border border-[#30363d] text-left">
                  <div className="text-[11px] font-mono uppercase text-[#d29922] font-semibold flex items-center gap-1.5 mb-1">
                    <Sparkles className="w-3.5 h-3.5" />
                    Dev Sandbox Token:
                  </div>
                  <div className="text-xs font-mono text-[#58a6ff] break-all select-all bg-[#161b22] p-2 rounded">
                    {devTokenNotice}
                  </div>
                </div>
              )}

              <button
                onClick={() => {
                  if (devTokenNotice) setToken(devTokenNotice);
                  setStep(4);
                }}
                className="w-full py-3 px-4 bg-[#1f6feb] hover:bg-[#388bfd] text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
              >
                <span>Enter Recovery Token</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <div className="text-xs text-[#8b949e]">
                Didn&apos;t receive it?{' '}
                <button
                  disabled={resendCooldown > 0}
                  onClick={handleRequestToken}
                  className="text-[#58a6ff] hover:underline disabled:opacity-50"
                >
                  Resend code {resendCooldown > 0 ? `(${resendCooldown}s)` : ''}
                </button>
              </div>
            </div>
          )}

          {/* STEP 4: Token input */}
          {step === 4 && (
            <div>
              <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-white">Verify Recovery Token</h2>
                <p className="text-xs text-[#8b949e] mt-1.5">
                  Paste the 64-character verification code delivered to your email.
                </p>
              </div>

              <form onSubmit={handleVerifyToken} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                    Security Token
                  </label>
                  <div className="relative">
                    <KeyRound className="w-5 h-5 absolute left-3 top-2.5 text-[#8b949e]" />
                    <input
                      type="text"
                      required
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      placeholder="Paste token here"
                      className="w-full pl-10 pr-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white font-mono text-xs focus:outline-none focus:border-[#1f6feb]"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting || token.length < 8}
                  className="w-full py-3 px-4 bg-[#1f6feb] hover:bg-[#388bfd] disabled:opacity-50 text-white font-semibold rounded-xl transition-all shadow-md flex items-center justify-center gap-2"
                >
                  <span>Verify Token</span>
                  <ArrowRight className="w-4 h-4" />
                </button>

                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="w-full text-xs text-[#8b949e] hover:text-white transition-colors"
                >
                  ← Request a different email
                </button>
              </form>
            </div>
          )}

          {/* STEP 5: Token verifying animation */}
          {step === 5 && (
            <div className="text-center py-8 space-y-4">
              <div className="w-14 h-14 rounded-full bg-[#1f6feb]/15 border border-[#1f6feb]/40 flex items-center justify-center mx-auto text-[#58a6ff]">
                <RefreshCw className="w-6 h-6 animate-spin" />
              </div>
              <h3 className="text-lg font-bold text-white">Verifying Token Signature…</h3>
              <p className="text-xs text-[#8b949e]">
                Checking token hash against database single-use ledger.
              </p>
            </div>
          )}

          {/* STEP 6: Enter new password */}
          {step === 6 && (
            <div>
              <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-white">Create New Password</h2>
                <p className="text-xs text-[#8b949e] mt-1.5">
                  Choose a strong, unique password for your account.
                </p>
              </div>

              <form onSubmit={handleResetPassword} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                    New Password
                  </label>
                  <div className="relative">
                    <Lock className="w-5 h-5 absolute left-3 top-2.5 text-[#8b949e]" />
                    <input
                      type="password"
                      required
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full pl-10 pr-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-sm focus:outline-none focus:border-[#1f6feb]"
                    />
                  </div>

                  {/* Password Strength Meter */}
                  <div className="mt-2 space-y-1">
                    <div className="flex justify-between text-[11px] text-[#8b949e]">
                      <span>Strength</span>
                      <span className={strength >= 75 ? 'text-[#2ea043]' : strength >= 50 ? 'text-[#d29922]' : 'text-red-400'}>
                        {strength >= 75 ? 'Strong' : strength >= 50 ? 'Medium' : 'Weak'}
                      </span>
                    </div>
                    <div className="w-full bg-[#21262d] h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 rounded-full ${
                          strength >= 75 ? 'bg-[#2ea043]' : strength >= 50 ? 'bg-[#d29922]' : 'bg-red-500'
                        }`}
                        style={{ width: `${strength}%` }}
                      ></div>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#c9d1d9] mb-1.5">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <Lock className="w-5 h-5 absolute left-3 top-2.5 text-[#8b949e]" />
                    <input
                      type="password"
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full pl-10 pr-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-white text-sm focus:outline-none focus:border-[#1f6feb]"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting || strength < 50 || newPassword !== confirmPassword}
                  className="w-full py-3 px-4 bg-[#238636] hover:bg-[#2ea043] disabled:opacity-50 text-white font-semibold rounded-xl transition-all shadow-md shadow-[#238636]/20 flex items-center justify-center gap-2"
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
              <div className="w-14 h-14 rounded-full bg-[#238636]/15 border border-[#238636]/40 flex items-center justify-center mx-auto text-[#2ea043]">
                <RefreshCw className="w-6 h-6 animate-spin" />
              </div>
              <h3 className="text-lg font-bold text-white">Updating Credentials…</h3>
              <p className="text-xs text-[#8b949e]">
                Invalidating prior sessions and updating cryptographic bcrypt hash.
              </p>
            </div>
          )}

          {/* STEP 8: Success Complete */}
          {step === 8 && (
            <div className="text-center py-6 space-y-5">
              <div className="w-16 h-16 rounded-full bg-[#238636]/20 border border-[#238636]/50 flex items-center justify-center mx-auto text-[#2ea043] shadow-lg shadow-[#238636]/20">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <div>
                <h3 className="text-2xl font-extrabold text-white">Password Reset Successful!</h3>
                <p className="text-sm text-[#8b949e] mt-2">
                  Your credentials have been securely updated. You can now sign in with your new password.
                </p>
              </div>

              <Link
                href="/login"
                className="w-full py-3 px-4 bg-[#1f6feb] hover:bg-[#388bfd] text-white font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
              >
                <span>Proceed to Sign In</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          )}

          <div className="mt-6 pt-4 border-t border-[#30363d] text-center">
            <Link href="/login" className="inline-flex items-center gap-1.5 text-xs text-[#8b949e] hover:text-white transition-colors">
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ForgotPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400 text-sm">Loading recovery portal...</div>}>
      <ForgotPasswordContent />
    </Suspense>
  );
}
