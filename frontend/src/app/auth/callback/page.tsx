'use client';

import { useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Sparkles } from 'lucide-react';

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get('token');
    const refreshToken = searchParams.get('refresh_token');
    const accountType = searchParams.get('type') || 'individual';
    const dest = searchParams.get('dest') || (accountType === 'enterprise' ? '/enterprise/dashboard' : '/individual/dashboard');

    if (token) {
      localStorage.setItem('token', token);
      localStorage.setItem('account_type', accountType);
      if (refreshToken) {
        localStorage.setItem('refresh_token', refreshToken);
      }
      router.replace(dest);
    } else {
      router.replace('/login?error=OAuth%20authentication%20failed');
    }
  }, [router, searchParams]);

  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center text-zinc-100 relative overflow-hidden">
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="w-[500px] h-[500px] bg-red-600/[0.08] blur-[140px] animate-aurora rounded-full absolute top-1/3 left-1/2 -translate-x-1/2" />
      </div>
      <div className="relative z-10 w-12 h-12 rounded-full bg-gradient-to-tr from-white/90 via-white/70 to-white/40 flex items-center justify-center text-black shadow-xl shadow-white/10 animate-pulse mb-4">
        <Sparkles className="w-5 h-5" />
      </div>
      <h2 className="relative z-10 text-lg font-semibold text-white">Authenticating session...</h2>
      <p className="relative z-10 text-xs text-zinc-500 mt-1">Connecting to your intelligent workspace</p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-black flex items-center justify-center text-xs text-zinc-500">Loading...</div>}>
      <CallbackHandler />
    </Suspense>
  );
}
