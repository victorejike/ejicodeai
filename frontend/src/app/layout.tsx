'use client';

import './globals.css';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useEffect, ReactNode } from 'react';

const PUBLIC_PATHS = ['/', '/login', '/register', '/forgot-password'];

const navLinks = [
  { href: '/individual/dashboard', label: 'Organization Hub (Get Hired)', icon: '👤' },
  { href: '/enterprise/dashboard', label: 'Enterprise Client Pipeline', icon: '🏢' },
  { href: '/dashboard', label: 'BD Command Center', icon: '⊞' },
  { href: '/opportunities', label: 'Client Opportunities', icon: '🎯' },
  { href: '/companies', label: 'Target Companies', icon: '🌐' },
  { href: '/contacts', label: 'Decision Makers', icon: '👥' },
  { href: '/research', label: 'Deep Research', icon: '🔬' },
  { href: '/proposals', label: 'Proposals & Pitches', icon: '📄' },
  { href: '/outreach', label: 'Outreach & Follow-Up', icon: '📧' },
  { href: '/agents', label: 'Agents & Workflows', icon: '🤖' },
  { href: '/settings', label: 'Settings', icon: '⚙' },
];

function Sidebar({ onLogout, theme, toggleTheme }: { onLogout: () => void; theme: string; toggleTheme: () => void }) {
  const pathname = usePathname();
  return (
    <aside className="hidden md:flex flex-col w-64 shrink-0 backdrop-blur-3xl bg-black/50 border-r border-white/10 min-h-screen relative z-20">
      {/* EJICODE_AI Logo Brand Asset */}
      <div className="flex items-center justify-between px-5 py-5 border-b border-white/10">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center shrink-0 shadow-md shadow-white/20 font-mono font-black text-black text-xs group-hover:scale-105 transition-transform">
            E
          </div>
          <div>
            <div className="text-white text-sm font-bold tracking-tight font-mono">EJICODE_AI</div>
            <div className="text-zinc-400 text-[10px] tracking-wide">Autonomous BD &amp; Placement</div>
          </div>
        </Link>
        <button
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          className="p-1.5 rounded-full hover:bg-white/10 text-zinc-400 hover:text-white transition-colors text-xs"
        >
          {theme === 'dark' ? '☀' : '🌙'}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 overflow-y-auto space-y-1 px-3">
        <div className="px-3 py-1.5 mb-1">
          <span className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold font-mono">Pipelines &amp; Tools</span>
        </div>
        {navLinks.map(({ href, label, icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3.5 py-2.5 rounded-full text-xs font-semibold transition-all ${
                active
                  ? 'bg-white/10 text-white border border-white/20 shadow-[0_4px_20px_rgba(255,255,255,0.06)]'
                  : 'text-zinc-400 hover:text-white hover:bg-white/[0.04] border border-transparent'
              }`}
            >
              <span className="text-sm leading-none">{icon}</span>
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-white/10 p-4 space-y-2">
        <div className="p-3 rounded-2xl apple-glass-subtle flex items-center gap-2.5">
          <div className="w-2 h-2 rounded-full bg-red-500 animate-ping shrink-0" />
          <div className="text-[10px] text-zinc-400 font-mono leading-tight">
            <span className="text-white font-bold">Autonomous Fleet:</span> Active
          </div>
        </div>
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs text-zinc-400 hover:text-red-400 hover:bg-white/[0.04] rounded-xl transition-colors"
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
    <header className="md:hidden backdrop-blur-2xl bg-black/60 border-b border-white/10 sticky top-0 z-50">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-white flex items-center justify-center font-mono font-bold text-black text-xs shadow-md">
            E
          </div>
          <span className="text-white text-sm font-bold font-mono">EJICODE_AI</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={toggleTheme} className="p-1.5 rounded-full hover:bg-white/10 text-zinc-400">
            {theme === 'dark' ? '☀' : '🌙'}
          </button>
          <button onClick={() => setOpen(!open)} className="p-1.5 rounded-full hover:bg-white/10 text-zinc-400">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {open ? <path d="M18 6L6 18M6 6l12 12"/> : <><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></>}
            </svg>
          </button>
        </div>
      </div>
      {open && (
        <nav className="border-t border-white/10 bg-black/90 backdrop-blur-3xl px-3 py-3 flex flex-col gap-1">
          {navLinks.map(({ href, label, icon }) => (
            <Link key={href} href={href} onClick={() => setOpen(false)}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs transition-colors ${
                pathname === href ? 'bg-white/10 text-white border border-white/20' : 'text-zinc-400 hover:text-white hover:bg-white/[0.04]'
              }`}>
              <span>{icon}</span> {label}
            </Link>
          ))}
          <button onClick={onLogout} className="text-left text-xs text-red-400 px-3 py-2 hover:bg-white/5 rounded-xl">Sign out</button>
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
    if (PUBLIC_PATHS.includes(pathname)) {
      setAuthed(true);
      return;
    }
    const token = localStorage.getItem('token');
    if (!token) {
      router.replace('/login');
    } else {
      setAuthed(true);
    }
  }, [pathname, router]);

  if (PUBLIC_PATHS.includes(pathname)) return <>{children}</>;
  if (authed === null) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#08080a]">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-red-500 animate-ping" />
          <div className="text-[#9ca3af] text-xs font-mono">Initializing EJICODE_AI Platform…</div>
        </div>
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
    localStorage.removeItem('account_type');
    router.push('/login');
  };

  const isPublic = PUBLIC_PATHS.includes(pathname);

  return (
    <html lang="en">
      <head>
        <title>EJICODE_AI — Autonomous AI Career Agent &amp; BD Platform</title>
      </head>
      <body className="bg-[#000000] min-h-screen text-[#f4f4f5] transition-colors duration-150 font-sans selection:bg-white selection:text-black">
        <AuthGuard>
          {isPublic ? (
            children
          ) : (
            <div className="flex min-h-screen bg-[#000000] relative overflow-x-hidden">
              {/* Subtle ambient aurora in dashboard background */}
              <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
                <div className="w-[600px] h-[600px] bg-red-600/[0.05] blur-[160px] animate-aurora rounded-full absolute -top-40 right-1/4" />
                <div className="w-[500px] h-[500px] bg-rose-600/[0.04] blur-[150px] animate-aurora-red rounded-full absolute bottom-10 left-1/3" />
              </div>

              <Sidebar onLogout={logout} theme={theme} toggleTheme={toggleTheme} />
              <div className="flex-1 flex flex-col min-w-0 relative z-10">
                <TopBar onLogout={logout} theme={theme} toggleTheme={toggleTheme} />
                <div className="hidden md:flex items-center justify-between backdrop-blur-2xl bg-black/40 border-b border-white/10 px-6 py-2.5 text-[11px] text-zinc-400 font-mono">
                  <div className="flex items-center gap-3">
                    <span className="text-white font-bold flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                      EJICODE_AI Fleet
                    </span>
                    <span className="text-zinc-700">•</span>
                    <span>Autonomous Organization Placement Fleet</span>
                    <span className="text-zinc-700">•</span>
                    <span className="flex items-center gap-1.5 text-emerald-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                      Continuous Opportunity Radar Online
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="px-2.5 py-0.5 rounded-full apple-glass-subtle text-zinc-300 text-[10px] font-bold">
                      APPLE DESIGN V2
                    </span>
                    <span>{currentTime || 'Synchronizing…'}</span>
                  </div>
                </div>
                <main className="flex-1 p-6 md:p-8 overflow-auto">
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
