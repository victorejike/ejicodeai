'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.error || 'Invalid credentials'); return; }
      localStorage.setItem('token', data.access_token);
      router.push('/');
      router.refresh();
    } catch {
      setError('Network error — is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-vscode-bg px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8 justify-center">
          <div className="w-10 h-10 rounded-lg bg-vscode-accent flex items-center justify-center">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <div className="text-vscode-text font-semibold text-lg leading-tight">Ejicode AI</div>
            <div className="text-vscode-muted text-xs">Business Development Platform</div>
          </div>
        </div>

        {/* Card */}
        <div className="bg-vscode-sidebar border border-vscode-border rounded-lg p-6">
          <h1 className="text-vscode-text font-semibold text-base mb-5">Sign in</h1>

          {error && (
            <div className="mb-4 rounded px-3 py-2 text-xs bg-red-900/40 border border-red-700/50 text-red-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-vscode-muted mb-1.5">Username</label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                autoFocus
                placeholder="admin"
                className="w-full bg-vscode-surface border border-vscode-border rounded px-3 py-2 text-sm text-vscode-text placeholder-vscode-muted focus:outline-none focus:border-vscode-accent transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs text-vscode-muted mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                className="w-full bg-vscode-surface border border-vscode-border rounded px-3 py-2 text-sm text-vscode-text placeholder-vscode-muted focus:outline-none focus:border-vscode-accent transition-colors"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-vscode-accent hover:bg-vscode-accent-hover disabled:opacity-50 text-white rounded px-4 py-2 text-sm font-medium transition-colors"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="mt-4 text-xs text-vscode-muted text-center">
            Default: <span className="text-vscode-text font-mono">admin / admin</span>
          </p>
        </div>
      </div>
    </div>
  );
}
