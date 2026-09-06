'use client';

import './globals.css';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useEffect, ReactNode } from 'react';

const navLinks = [
  { href: '/', label: 'Dashboard', icon: '⊞' },
  { href: '/companies', label: 'Companies', icon: '🏢' },
  { href: '/opportunities', label: 'Opportunities', icon: '🎯' },
  { href: '/contacts', label: 'Contacts', icon: '👤' },
  { href: '/research', label: 'Research', icon: '🔬' },
  { href: '/proposals', label: 'Proposals', icon: '📄' },
  { href: '/outreach', label: 'Outreach', icon: '📧' },
  { href: '/agents', label: 'Agents', icon: '🤖' },
  { href: '/settings', label: 'Settings', icon: '⚙' },
];

function Sidebar({ onLogout, theme, toggleTheme }: { onLogout: () => void; theme: string; toggleTheme: () => void }) {
  const pathname = usePathname();
  return (
    <aside className="hidden md:flex flex-col w-60 shrink-0 bg-vscode-sidebar border-r border-vscode-border min-h-screen">
      {/* Logo */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-vscode-border">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded bg-vscode-accent flex items-center justify-center shrink-0 shadow-sm">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <div className="text-vscode-text text-sm font-semibold leading-tight">Ejicode AI</div>
            <div className="text-vscode-muted text-[10px]">BD Platform</div>
          </div>
        </div>
        <button
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          className="p-1.5 rounded hover:bg-vscode-surface text-vscode-muted hover:text-vscode-text transition-colors text-xs"
        >
          {theme === 'dark' ? '☀' : '🌙'}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-2 overflow-y-auto">
        <div className="px-3 py-1.5">
          <span className="text-[10px] uppercase tracking-widest text-vscode-muted font-semibold px-2">Navigation</span>
        </div>
        {navLinks.map(({ href, label, icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2.5 px-5 py-2 text-sm transition-colors ${
                active
                  ? 'bg-vscode-accent-light text-white font-medium border-l-2 border-vscode-accent'
                  : 'text-vscode-muted hover:text-vscode-text hover:bg-vscode-surface border-l-2 border-transparent'
              }`}
            >
              <span className="text-base leading-none">{icon}</span>
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-vscode-border p-3 space-y-1">
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs text-vscode-muted hover:text-vscode-red hover:bg-vscode-surface rounded transition-colors"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/>
          </svg>
          Sign out
        </button>
      </div>
    </aside>
  );
}

function TopBar({ onLogout, theme, toggleTheme }: { onLogout: () => void; theme: string; toggleTheme: () => void }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <header className="md:hidden bg-vscode-sidebar border-b border-vscode-border sticky top-0 z-50">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-vscode-accent flex items-center justify-center">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="text-vscode-text text-sm font-semibold">Ejicode AI</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={toggleTheme} className="p-1.5 rounded hover:bg-vscode-surface text-vscode-muted">
            {theme === 'dark' ? '☀' : '🌙'}
          </button>
          <button onClick={() => setOpen(!open)} className="p-1.5 rounded hover:bg-vscode-surface text-vscode-muted">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {open ? <path d="M18 6L6 18M6 6l12 12"/> : <><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></>}
            </svg>
          </button>
        </div>
      </div>
      {open && (
        <nav className="border-t border-vscode-border bg-vscode-sidebar px-3 py-2 flex flex-col gap-0.5">
          {navLinks.map(({ href, label, icon }) => (
            <Link key={href} href={href} onClick={() => setOpen(false)}
              className={`flex items-center gap-2.5 px-3 py-2 rounded text-sm transition-colors ${
                pathname === href ? 'bg-vscode-accent-light text-white' : 'text-vscode-muted hover:text-vscode-text hover:bg-vscode-surface'
              }`}>
              <span>{icon}</span> {label}
            </Link>
          ))}
          <button onClick={onLogout} className="text-left text-xs text-vscode-red px-3 py-2">Sign out</button>
        </nav>
      )}
    </header>
  );
}

function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token && pathname !== '/login') {
      router.replace('/login');
    } else {
      setAuthed(true);
    }
  }, [pathname, router]);

  if (pathname === '/login') return <>{children}</>;
  if (authed === null) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-vscode-bg">
        <div className="text-vscode-muted text-sm animate-pulse">Initializing Ejicode AI Platform…</div>
      </div>
    );
  }
  return <>{children}</>;
}

export default function RootLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [theme, setTheme] = useState('dark');
  const [currentTime, setCurrentTime] = useState('');

  useEffect(() => {
    const saved = localStorage.getItem('theme') || 'dark';
    setTheme(saved);
    if (saved === 'light') {
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
    }
    setCurrentTime(new Date().toLocaleTimeString());
    const interval = setInterval(() => setCurrentTime(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(interval);
  }, []);

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    localStorage.setItem('theme', next);
    if (next === 'light') {
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  const isLogin = pathname === '/login';

  return (
    <html lang="en">
      <body className="bg-vscode-bg min-h-screen text-vscode-text transition-colors duration-150">
        <AuthGuard>
          {isLogin ? (
            children
          ) : (
            <div className="flex min-h-screen">
              <Sidebar onLogout={logout} theme={theme} toggleTheme={toggleTheme} />
              <div className="flex-1 flex flex-col min-w-0">
                <TopBar onLogout={logout} theme={theme} toggleTheme={toggleTheme} />
                {/* Enterprise Status bar */}
                <div className="hidden md:flex items-center justify-between bg-vscode-accent px-4 py-1 text-[11px] text-white/90 font-medium">
                  <div className="flex items-center gap-3">
                    <span>⚡ Ejicode AI BD Engine</span>
                    <span>•</span>
                    <span>Model: Gemini 2.5 Flash</span>
                    <span>•</span>
                    <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span> Live Pipeline Active</span>
                  </div>
                  <span>{currentTime || 'Synchronizing…'}</span>
                </div>
                <main className="flex-1 p-6 overflow-auto">
                  {children}
                </main>
              </div>
            </div>
          )}
        </AuthGuard>
      </body>
    </html>
  );
}
