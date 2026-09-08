'use client';

import './globals.css';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useEffect, ReactNode } from 'react';
import {
  Bot,
  Building2,
  FileSignature,
  FileText,
  FlaskConical,
  Globe,
  LayoutGrid,
  LogOut,
  Mail,
  Menu,
  Moon,
  Settings,
  Sun,
  Target,
  User,
  UserCog,
  Users,
  X,
  type LucideIcon,
} from 'lucide-react';
import { useSession } from '@/lib/useSession';

const PUBLIC_PATHS = ['/', '/login', '/register', '/forgot-password'];

type Audience = 'individual' | 'enterprise' | 'admin';

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  audience: Audience[];
}

/**
 * One declaration of the navigation, tagged by who it is for. Showing a
 * candidate the BD command centre (and an enterprise user the CV builder) was
 * the old behaviour; the audience tags are what fix it.
 */
const NAV_ITEMS: NavItem[] = [
  { href: '/individual/dashboard', label: 'Career Hub', icon: User, audience: ['individual'] },
  { href: '/individual/profile', label: 'My Profile', icon: UserCog, audience: ['individual'] },
  { href: '/individual/cv-builder', label: 'ATS CV Builder', icon: FileText, audience: ['individual'] },
  { href: '/enterprise/dashboard', label: 'Client Pipeline', icon: Building2, audience: ['enterprise', 'admin'] },
  { href: '/dashboard', label: 'BD Command Center', icon: LayoutGrid, audience: ['admin'] },
  { href: '/opportunities', label: 'Opportunities', icon: Target, audience: ['individual', 'enterprise', 'admin'] },
  { href: '/companies', label: 'Target Companies', icon: Globe, audience: ['enterprise', 'admin'] },
  { href: '/contacts', label: 'Decision Makers', icon: Users, audience: ['enterprise', 'admin'] },
  { href: '/research', label: 'Deep Research', icon: FlaskConical, audience: ['enterprise', 'admin'] },
  { href: '/proposals', label: 'Proposals & Pitches', icon: FileSignature, audience: ['enterprise', 'admin'] },
  { href: '/outreach', label: 'Outreach & Follow-Up', icon: Mail, audience: ['enterprise', 'admin'] },
  { href: '/agents', label: 'Agents & Workflows', icon: Bot, audience: ['individual', 'enterprise', 'admin'] },
  { href: '/settings', label: 'Settings', icon: Settings, audience: ['individual', 'enterprise', 'admin'] },
];

function visibleNav(accountType: string | null, isSuperuser: boolean): NavItem[] {
  const audiences = new Set<Audience>();
  if (isSuperuser) audiences.add('admin');
  if (accountType === 'enterprise') audiences.add('enterprise');
  // Default to the candidate view: it is the only one that works without an
  // organization, and it is what an unresolved session most likely is.
  if (accountType === 'individual' || !accountType) audiences.add('individual');
  return NAV_ITEMS.filter((item) => item.audience.some((a) => audiences.has(a)));
}

function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavList({ items, onNavigate }: { items: NavItem[]; onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <>
      {items.map(({ href, label, icon: Icon }) => {
        const active = isActive(pathname, href);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            aria-current={active ? 'page' : undefined}
            className={`flex items-center gap-3 rounded-full border px-3.5 py-2.5 text-xs font-semibold transition-all ${
              active
                ? 'apple-glass-subtle border-[var(--border)] text-[var(--text)]'
                : 'border-transparent text-[var(--text-muted)] hover:bg-[var(--glass-hover-bg)] hover:text-[var(--text)]'
            }`}
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span className="truncate">{label}</span>
          </Link>
        );
      })}
    </>
  );
}

function Brand({
  compact = false,
  avatarUrl = null,
  displayName = null,
  firstName = null,
}: {
  compact?: boolean;
  avatarUrl?: string | null;
  displayName?: string | null;
  firstName?: string | null;
}) {
  const hasAvatar = Boolean(avatarUrl);
  const initial = (firstName || displayName || 'E').charAt(0).toUpperCase();

  return (
    <Link href="/" className="group flex items-center gap-3">
      {hasAvatar ? (
        <div
          className={`relative shrink-0 overflow-hidden rounded-full border-2 border-red-500/80 shadow-[0_0_16px_rgba(239,68,68,0.5)] ring-2 ring-red-500/25 transition-all duration-300 group-hover:scale-105 group-hover:shadow-[0_0_24px_rgba(239,68,68,0.7)] ${
            compact ? 'h-8 w-8' : 'h-10 w-10'
          }`}
        >
          <img
            src={avatarUrl!}
            alt={displayName || 'Profile'}
            className="h-full w-full object-cover"
          />
          <span className="absolute inset-0 rounded-full ring-1 ring-inset ring-white/20 pointer-events-none" />
        </div>
      ) : displayName ? (
        <div
          className={`relative flex shrink-0 items-center justify-center rounded-full bg-gradient-to-tr from-red-600 via-rose-500 to-amber-500 font-mono text-xs font-black text-white shadow-[0_0_15px_rgba(239,68,68,0.4)] ring-2 ring-red-500/20 transition-transform group-hover:scale-105 ${
            compact ? 'h-8 w-8' : 'h-10 w-10'
          }`}
        >
          {initial}
          <span className="absolute inset-0 rounded-full ring-1 ring-inset ring-white/20 pointer-events-none" />
        </div>
      ) : (
        <div
          className={`flex shrink-0 items-center justify-center rounded-full bg-[var(--btn-primary-bg)] font-mono text-xs font-black text-[var(--btn-primary-fg)] transition-transform group-hover:scale-105 shadow-[0_0_15px_rgba(239,68,68,0.3)] border border-red-500/40 ${
            compact ? 'h-7 w-7' : 'h-8 w-8'
          }`}
        >
          E
        </div>
      )}
      {compact ? (
        <span className="font-mono text-sm font-bold text-[var(--text)] truncate max-w-[130px]">
          {displayName || 'EJICODE_AI'}
        </span>
      ) : (
        <div className="min-w-0">
          <div className="font-mono text-sm font-bold tracking-tight text-[var(--text)] truncate">
            {displayName || 'EJICODE_AI'}
          </div>
          <div className="text-[10px] tracking-wide text-[var(--text-muted)] truncate">
            {displayName ? 'Verified Candidate Profile' : 'Autonomous Career Agents'}
          </div>
        </div>
      )}
    </Link>
  );
}

function ThemeButton({ theme, toggleTheme }: { theme: string; toggleTheme: () => void }) {
  return (
    <button
      onClick={toggleTheme}
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      className="rounded-full p-1.5 text-[var(--text-muted)] transition-colors hover:bg-[var(--glass-hover-bg)] hover:text-[var(--text)]"
    >
      {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}

function Sidebar({
  items,
  onLogout,
  theme,
  toggleTheme,
  avatarUrl,
  displayName,
  firstName,
}: {
  items: NavItem[];
  onLogout: () => void;
  theme: string;
  toggleTheme: () => void;
  avatarUrl?: string | null;
  displayName?: string | null;
  firstName?: string | null;
}) {
  return (
    <aside className="relative z-20 hidden min-h-screen w-64 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--sidebar)] backdrop-blur-3xl md:flex">
      <div className="flex items-center justify-between border-b border-[var(--border)] px-5 py-5">
        <Brand avatarUrl={avatarUrl} displayName={displayName} firstName={firstName} />
        <ThemeButton theme={theme} toggleTheme={toggleTheme} />
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        <div className="mb-1 px-3 py-1.5">
          <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
            Pipelines &amp; Tools
          </span>
        </div>
        <NavList items={items} />
      </nav>

      <div className="border-t border-[var(--border)] p-4">
        <button
          onClick={onLogout}
          className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-xs text-[var(--text-muted)] transition-colors hover:bg-[var(--glass-hover-bg)] hover:text-[var(--red)]"
        >
          <LogOut className="h-3.5 w-3.5" />
          Sign out
        </button>
      </div>
    </aside>
  );
}

function TopBar({
  items,
  onLogout,
  theme,
  toggleTheme,
  avatarUrl,
  displayName,
  firstName,
}: {
  items: NavItem[];
  onLogout: () => void;
  theme: string;
  toggleTheme: () => void;
  avatarUrl?: string | null;
  displayName?: string | null;
  firstName?: string | null;
}) {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--sidebar)] backdrop-blur-2xl md:hidden">
      <div className="flex items-center justify-between px-4 py-3">
        <Brand compact avatarUrl={avatarUrl} displayName={displayName} firstName={firstName} />
        <div className="flex items-center gap-2">
          <ThemeButton theme={theme} toggleTheme={toggleTheme} />
          <button
            onClick={() => setOpen(!open)}
            aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open}
            className="rounded-full p-1.5 text-[var(--text-muted)] hover:bg-[var(--glass-hover-bg)]"
          >
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>
      {open && (
        <nav className="flex flex-col gap-1 border-t border-[var(--border)] bg-[var(--sidebar)] px-3 py-3 backdrop-blur-3xl">
          <NavList items={items} onNavigate={() => setOpen(false)} />
          <button
            onClick={onLogout}
            className="rounded-xl px-3 py-2 text-left text-xs text-[var(--red)] hover:bg-[var(--glass-hover-bg)]"
          >
            Sign out
          </button>
        </nav>
      )}
    </header>
  );
}

/**
 * The signed-in chrome. Split out from `RootLayout` so `useSession()` is only
 * mounted behind the auth guard - the login page must not fire an authenticated
 * request it is guaranteed to fail.
 */
function AppChrome({
  children,
  theme,
  toggleTheme,
  onLogout,
}: {
  children: ReactNode;
  theme: string;
  toggleTheme: () => void;
  onLogout: () => void;
}) {
  const { firstName, displayName, accountType, user, avatarUrl, completion, agentReady, loading } = useSession();
  const items = visibleNav(accountType, Boolean(user?.is_superuser));
  const percent = completion?.percent ?? null;

  return (
    <div className="relative flex min-h-screen overflow-x-hidden bg-[var(--bg)]">
      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        <div className="animate-aurora absolute -top-40 right-1/4 h-[600px] w-[600px] rounded-full bg-red-600/[0.05] blur-[160px]" />
        <div className="animate-aurora-red absolute bottom-10 left-1/3 h-[500px] w-[500px] rounded-full bg-rose-600/[0.04] blur-[150px]" />
      </div>

      <Sidebar
        items={items}
        onLogout={onLogout}
        theme={theme}
        toggleTheme={toggleTheme}
        avatarUrl={avatarUrl}
        displayName={displayName}
        firstName={firstName}
      />
      <div className="relative z-10 flex min-w-0 flex-1 flex-col">
        <TopBar
          items={items}
          onLogout={onLogout}
          theme={theme}
          toggleTheme={toggleTheme}
          avatarUrl={avatarUrl}
          displayName={displayName}
          firstName={firstName}
        />

        {/* Identity strip: the greeting the user asked for, on every page with glowing avatar. */}
        <div className="hidden items-center justify-between gap-4 border-b border-[var(--border)] bg-[var(--sidebar)] px-6 py-2.5 text-[11px] text-[var(--text-muted)] backdrop-blur-2xl md:flex">
          <div className="flex min-w-0 items-center gap-3">
            {avatarUrl ? (
              <div className="relative h-6 w-6 shrink-0 overflow-hidden rounded-full border border-red-500/80 shadow-[0_0_10px_rgba(239,68,68,0.5)] ring-1 ring-red-500/30">
                <img src={avatarUrl} alt={displayName || 'User'} className="h-full w-full object-cover" />
              </div>
            ) : firstName || displayName ? (
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-red-600/30 border border-red-500/50 text-[10px] font-bold text-red-300">
                {(firstName || displayName || 'U').charAt(0).toUpperCase()}
              </div>
            ) : null}
            {loading ? (
              <span className="skeleton-shimmer h-3 w-40 rounded" />
            ) : firstName || displayName ? (
              <span className="truncate font-semibold text-[var(--text)]">
                Welcome, {firstName || displayName}
              </span>
            ) : (
              <Link href="/individual/profile" className="font-semibold text-[var(--text)] underline">
                Add your name to your profile
              </Link>
            )}
            {user?.email && (
              <>
                <span className="text-[var(--border)]">•</span>
                <span className="truncate font-mono">{user.email}</span>
              </>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-3">
            {!loading && percent !== null && (
              <Link
                href="/individual/profile"
                title={
                  agentReady
                    ? 'Your profile is complete - the agents can run'
                    : 'Finish your profile to unlock the agents'
                }
                className="apple-glass-subtle flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-bold"
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    agentReady ? 'bg-[var(--green)]' : 'bg-[var(--yellow)]'
                  }`}
                />
                {agentReady ? 'Profile complete' : `Profile ${percent}%`}
              </Link>
            )}
          </div>
        </div>

        <main className="flex-1 overflow-auto p-6 md:p-8">{children}</main>
      </div>
    </div>
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
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg)]">
        <div className="flex items-center gap-3">
          <div className="h-3 w-3 animate-ping rounded-full bg-[var(--accent)]" />
          <div className="font-mono text-xs text-[var(--text-muted)]">Loading your workspace…</div>
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

  useEffect(() => {
    const saved = localStorage.getItem('theme') || 'dark';
    setTheme(saved);
    document.documentElement.classList.toggle('light', saved === 'light');
  }, []);

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    localStorage.setItem('theme', next);
    document.documentElement.classList.toggle('light', next === 'light');
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
      <body className="min-h-screen bg-[var(--bg)] font-sans text-[var(--text)] transition-colors duration-150 selection:bg-[var(--accent)] selection:text-white">
        <AuthGuard>
          {isPublic ? (
            children
          ) : (
            <AppChrome theme={theme} toggleTheme={toggleTheme} onLogout={logout}>
              {children}
            </AppChrome>
          )}
        </AuthGuard>
      </body>
    </html>
  );
}
