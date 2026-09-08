'use client';

import { useMemo, useState } from 'react';
import useSWR from 'swr';
import {
  AlertTriangle,
  Check,
  Download,
  FileText,
  Loader2,
  RefreshCw,
  Sparkles,
  X,
} from 'lucide-react';
import ProfileGate from '@/components/ProfileGate';
import {
  Alert,
  AppShell,
  Badge,
  Button,
  Card,
  EmptyState,
  ProgressBar,
  ScoreRing,
  SectionHeader,
  cx,
} from '@/components/ui';
import { ApiError, apiPost, downloadFile, fetcher } from '@/lib/api';
import { useSession } from '@/lib/useSession';

interface CVVersion {
  id: string;
  version: number;
  label: string;
  target_title: string | null;
  target_company: string | null;
  opportunity_id: string | null;
  ats_score: number | null;
  keywords_matched: string[];
  keywords_missing: string[];
  generator: string | null;
  is_general: boolean;
  created_at: string | null;
  formats: string[];
}

interface CVDetail extends CVVersion {
  content_text: string | null;
  sections: Record<string, string>;
  cover_letter: string | null;
  ats_breakdown: {
    components?: Record<string, number>;
    maximums?: Record<string, number>;
    measured_out_of?: number;
    word_count?: number;
    recommendations?: string[];
    keywords_required?: string[];
  };
  format_warnings: string[];
  updated_at: string | null;
}

const FACTOR_LABELS: Record<string, string> = {
  keyword_coverage: 'Keyword coverage',
  format_safety: 'Format safety',
  section_completeness: 'Section completeness',
  readability: 'Readability',
  contact_block: 'Contact block',
};

function factorLabel(key: string): string {
  return FACTOR_LABELS[key] ?? key.replace(/_/g, ' ');
}

function KeywordList({
  words,
  tone,
  title,
  note,
}: {
  words: string[];
  tone: 'success' | 'warning';
  title: string;
  note: string;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <span className="text-xs font-semibold text-[var(--text)]">{title}</span>
        <Badge tone={words.length ? tone : 'unknown'}>{words.length || '—'}</Badge>
      </div>
      {words.length === 0 ? (
        <p className="text-[11px] text-[var(--text-muted)]">{note}</p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {words.map((word) => (
            <span
              key={word}
              className={cx(
                'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px]',
                tone === 'success'
                  ? 'border-[color:color-mix(in_srgb,var(--green)_35%,transparent)] text-[var(--green)]'
                  : 'border-dashed border-[var(--border)] text-[var(--text-muted)]'
              )}
            >
              {tone === 'success' ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
              {word}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function CVBuilderPage() {
  const { completion, agentReady, gateReason, loading: sessionLoading, refresh } = useSession();

  const [targetId, setTargetId] = useState<string>('');
  const [useAi, setUseAi] = useState(true);
  const [building, setBuilding] = useState(false);
  const [checking, setChecking] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [gated, setGated] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const versionsRes = useSWR<{ versions: CVVersion[]; best_ats_score: number | null }>(
    '/api/individual/cv/versions?limit=25',
    fetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );

  // Optional: tailoring targets come from this user's own matches. If the list
  // is unavailable the page still builds a general CV.
  const matchesRes = useSWR<any>('/api/individual/matches?limit=25', fetcher, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  const targets = useMemo(() => {
    const raw = matchesRes.data?.matches ?? matchesRes.data?.opportunities ?? [];
    if (!Array.isArray(raw)) return [] as { id: string; label: string }[];
    return raw
      .map((m: any) => {
        const id = m?.id ?? m?.opportunity_id;
        if (!id) return null;
        const company = m?.company_name ?? m?.company ?? null;
        return {
          id: String(id),
          label: [m?.title ?? 'Untitled role', company].filter(Boolean).join(' — '),
        };
      })
      .filter(Boolean) as { id: string; label: string }[];
  }, [matchesRes.data]);

  const versions = versionsRes.data?.versions ?? [];
  const activeId = selectedId ?? versions[0]?.id ?? null;

  const detailRes = useSWR<{ cv: CVDetail }>(
    activeId ? `/api/individual/cv/${activeId}` : null,
    fetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  const cv = detailRes.data?.cv ?? null;

  const handleError = (err: unknown, fallback: string) => {
    if (err instanceof ApiError) {
      setGated(err.isProfileGate);
      setError(err.message || fallback);
      if (err.isProfileGate) refresh();
      return;
    }
    setGated(false);
    setError(fallback);
  };

  const build = async () => {
    setBuilding(true);
    setError(null);
    setGated(false);
    setNotice(null);
    try {
      const res = await apiPost<{ cv: CVDetail | null; summary_source?: string }>(
        '/api/individual/cv/build',
        { opportunity_id: targetId || null, use_ai: useAi }
      );
      if (res.cv?.id) setSelectedId(res.cv.id);
      setNotice(
        res.summary_source === 'ai'
          ? 'Built with the AI writer, from your profile only.'
          : 'Built with the deterministic template (no AI provider configured).'
      );
      await versionsRes.mutate();
    } catch (err) {
      handleError(err, 'Could not build the CV.');
    } finally {
      setBuilding(false);
    }
  };

  const recheck = async () => {
    if (!activeId) return;
    setChecking(true);
    setError(null);
    try {
      await apiPost(`/api/individual/cv/${activeId}/ats-check`, {});
      await Promise.all([detailRes.mutate(), versionsRes.mutate()]);
      setNotice('Re-scored against the stored CV text.');
    } catch (err) {
      handleError(err, 'Could not re-check the CV.');
    } finally {
      setChecking(false);
    }
  };

  const download = async (format: string) => {
    if (!activeId) return;
    setError(null);
    try {
      await downloadFile(
        `/api/individual/cv/${activeId}/download?format=${format}`,
        `cv.${format}`
      );
    } catch (err) {
      handleError(err, `Could not download the ${format.toUpperCase()} file.`);
    }
  };

  const components = cv?.ats_breakdown?.components ?? {};
  const maximums = cv?.ats_breakdown?.maximums ?? {};
  const factorKeys = Object.keys(components);

  return (
    <AppShell
      eyebrow="Individual"
      title="ATS CV Builder"
      description="One CV per target role, assembled from your profile and checked against the rules real applicant tracking systems enforce. Nothing you have not claimed is ever added."
      banner={<ProfileGate completion={completion} loading={sessionLoading} />}
      actions={
        <Button
          onClick={build}
          loading={building}
          disabledReason={!agentReady ? gateReason ?? 'Finish your profile first.' : undefined}
          icon={<Sparkles className="h-4 w-4" />}
        >
          {building ? 'Building…' : 'Build CV'}
        </Button>
      }
    >
      {error && (
        <Alert
          tone={gated ? 'warning' : 'danger'}
          icon={<AlertTriangle className="h-4 w-4" />}
          title={gated ? 'Finish your profile first' : 'Something went wrong'}
          action={
            gated ? (
              <Button href="/individual/profile" size="sm" variant="secondary">
                Open profile
              </Button>
            ) : undefined
          }
        >
          {error}
        </Alert>
      )}
      {notice && !error && (
        <Alert tone="info" icon={<FileText className="h-4 w-4" />}>
          {notice}
        </Alert>
      )}

      <Card padding="lg">
        <SectionHeader
          title="Target"
          description="Tailoring to a specific job is what lifts keyword coverage. A general CV is still ATS-safe."
        />
        <div className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-[var(--text-muted)]">
              Tailor to one of your matches
            </span>
            <select
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              className="w-full rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-2.5 text-sm text-[var(--text)] outline-none focus:border-[var(--border-red)]"
            >
              <option value="">General CV (no specific job)</option>
              {targets.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
            {targets.length === 0 && (
              <span className="mt-1.5 block text-[11px] text-[var(--text-muted)]">
                No matches stored yet — run the agents to collect targets.
              </span>
            )}
          </label>

          <label className="flex cursor-pointer items-center gap-2 pb-2.5 text-xs text-[var(--text-muted)]">
            <input
              type="checkbox"
              checked={useAi}
              onChange={(e) => setUseAi(e.target.checked)}
              className="h-3.5 w-3.5 accent-[var(--accent)]"
            />
            Use the AI writer when a key is configured
          </label>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <Card padding="none" className="overflow-hidden">
          <div className="border-b border-[var(--border)] px-4 py-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              Versions
            </span>
          </div>
          {versionsRes.isLoading ? (
            <div className="space-y-2 p-3">
              {[0, 1, 2].map((i) => (
                <div key={i} className="skeleton-shimmer h-14 rounded-xl" />
              ))}
            </div>
          ) : versions.length === 0 ? (
            <p className="px-4 py-6 text-center text-[11px] text-[var(--text-muted)]">
              No CV built yet.
            </p>
          ) : (
            <ul className="max-h-[520px] divide-y divide-[var(--border)] overflow-y-auto">
              {versions.map((v) => (
                <li key={v.id}>
                  <button
                    onClick={() => setSelectedId(v.id)}
                    className={cx(
                      'w-full px-4 py-3 text-left transition-colors',
                      v.id === activeId
                        ? 'bg-[var(--glass-hover-bg)]'
                        : 'hover:bg-[var(--glass-hover-bg)]'
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-xs font-semibold text-[var(--text)]">
                        {v.label}
                      </span>
                      <Badge tone={v.ats_score === null ? 'unknown' : v.ats_score >= 80 ? 'success' : 'warning'}>
                        {v.ats_score === null ? '—' : v.ats_score}
                      </Badge>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-[10px] text-[var(--text-muted)]">
                      <span>v{v.version}</span>
                      {v.created_at && <span>{new Date(v.created_at).toLocaleDateString()}</span>}
                      {v.generator && <span>{v.generator}</span>}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="space-y-6">
          {!activeId ? (
            <EmptyState
              icon={<FileText className="h-5 w-5" />}
              title="No CV yet"
              description="Build one from your profile. It comes out single-column, with the standard headings an ATS parser expects, in .txt, .docx and .pdf."
              action={
                <Button
                  onClick={build}
                  loading={building}
                  disabledReason={!agentReady ? gateReason ?? 'Finish your profile first.' : undefined}
                >
                  Build my first CV
                </Button>
              }
            />
          ) : detailRes.isLoading || !cv ? (
            <Card className="h-64 skeleton-shimmer" padding="none" />
          ) : (
            <>
              <Card padding="lg">
                <div className="flex flex-wrap items-start justify-between gap-6">
                  <div className="flex items-center gap-6">
                    <ScoreRing value={cv.ats_score} label="ATS score" />
                    <div className="min-w-0">
                      <h2 className="text-sm font-semibold text-[var(--text)]">{cv.label}</h2>
                      <p className="mt-1 text-xs text-[var(--text-muted)]">
                        {cv.is_general
                          ? 'General CV — not tied to one posting'
                          : `Tailored to ${cv.target_title ?? 'a role'}${
                              cv.target_company ? ` at ${cv.target_company}` : ''
                            }`}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-[var(--text-muted)]">
                        <Badge tone="neutral">v{cv.version}</Badge>
                        {cv.ats_breakdown?.word_count ? (
                          <Badge tone="neutral">{cv.ats_breakdown.word_count} words</Badge>
                        ) : null}
                        {cv.generator && <Badge tone="info">{cv.generator}</Badge>}
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {(cv.formats ?? ['txt', 'docx', 'pdf']).map((format) => (
                      <Button
                        key={format}
                        variant="secondary"
                        size="sm"
                        onClick={() => download(format)}
                        icon={<Download className="h-3.5 w-3.5" />}
                      >
                        {format.toUpperCase()}
                      </Button>
                    ))}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={recheck}
                      loading={checking}
                      icon={<RefreshCw className="h-3.5 w-3.5" />}
                    >
                      Re-check
                    </Button>
                  </div>
                </div>

                {factorKeys.length > 0 ? (
                  <div className="mt-6 grid gap-4 sm:grid-cols-2">
                    {factorKeys.map((key) => {
                      const max = maximums[key] ?? 0;
                      const got = components[key] ?? 0;
                      const pct = max > 0 ? (100 * got) / max : 0;
                      return (
                        <ProgressBar
                          key={key}
                          value={pct}
                          autoTone
                          label={`${factorLabel(key)} — ${got}/${max || '—'}`}
                          size="sm"
                        />
                      );
                    })}
                  </div>
                ) : (
                  <p className="mt-6 text-[11px] text-[var(--text-muted)]">
                    No score breakdown stored for this version. Run “Re-check” to measure it.
                  </p>
                )}

                {cv.format_warnings?.length > 0 && (
                  <Alert
                    tone="warning"
                    className="mt-5"
                    icon={<AlertTriangle className="h-4 w-4" />}
                    title="Format notes"
                  >
                    <ul className="list-disc space-y-0.5 pl-4 text-xs">
                      {cv.format_warnings.map((w) => (
                        <li key={w}>{w}</li>
                      ))}
                    </ul>
                  </Alert>
                )}
              </Card>

              <Card padding="lg">
                <SectionHeader
                  title="Keywords"
                  description="Matched terms come from skills you actually list. Missing ones are suggestions for you to add truthfully — they are never written into the CV for you."
                />
                <div className="grid gap-6 sm:grid-cols-2">
                  <KeywordList
                    words={cv.keywords_matched ?? []}
                    tone="success"
                    title="Matched"
                    note="No overlap measured — build against a specific job to compare."
                  />
                  <KeywordList
                    words={cv.keywords_missing ?? []}
                    tone="warning"
                    title="Missing from your profile"
                    note="Nothing missing for this target."
                  />
                </div>
                {cv.ats_breakdown?.recommendations?.length ? (
                  <ul className="mt-6 space-y-1.5 border-t border-[var(--border)] pt-4 text-xs text-[var(--text-muted)]">
                    {cv.ats_breakdown.recommendations.map((r) => (
                      <li key={r} className="flex gap-2">
                        <span className="text-[var(--accent)]">•</span>
                        {r}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </Card>

              <Card padding="lg">
                <SectionHeader
                  title="Exactly what a parser reads"
                  description="Plain text, single column, standard headings. If it looks right here, it survives the robot."
                />
                {cv.content_text ? (
                  <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-xl border border-[var(--border)] bg-[var(--glass-subtle-bg)] p-4 font-mono text-[11px] leading-relaxed text-[var(--text)]">
                    {cv.content_text}
                  </pre>
                ) : (
                  <p className="text-[11px] text-[var(--text-muted)]">
                    No stored text for this version.
                  </p>
                )}
              </Card>

              {cv.cover_letter && (
                <Card padding="lg">
                  <SectionHeader title="Cover letter" />
                  <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-xs leading-relaxed text-[var(--text-muted)]">
                    {cv.cover_letter}
                  </pre>
                </Card>
              )}
            </>
          )}
        </div>
      </div>

      {(building || checking) && (
        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Working…
        </div>
      )}
    </AppShell>
  );
}
