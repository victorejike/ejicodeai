'use client';

import { AlertTriangle, ArrowRight, CheckCircle2, UploadCloud } from 'lucide-react';
import type { ProfileCompletion } from '@/lib/api';
import { Alert, Badge, Button, Card, ProgressBar, cx } from './ui';

/**
 * The profile checklist and the agent gate, in one place.
 *
 * Both the dashboard and the CV builder need to say the same thing about the
 * same profile, and the list is always the backend's own `missing_fields` - no
 * page invents its own idea of what "complete" means.
 */
export default function ProfileGate({
  completion,
  loading = false,
  className,
}: {
  completion: ProfileCompletion | null;
  loading?: boolean;
  className?: string;
}) {
  if (loading) {
    return <Card tone="subtle" className={cx('h-28 skeleton-shimmer', className)} padding="none" />;
  }
  if (!completion) return null;

  if (completion.agent_ready) {
    return (
      <Alert
        tone="success"
        icon={<CheckCircle2 className="h-4 w-4" />}
        title="Profile complete"
        className={className}
        action={
          <Button href="/individual/profile" variant="ghost" size="sm">
            Review
          </Button>
        }
      >
        Your agents have everything they need to search with your real data.
      </Alert>
    );
  }

  const missing = completion.missing_fields ?? [];
  const blocking = new Set((completion.blocking_fields ?? []).map((f) => f.key));

  return (
    <Card tone="glass" padding="lg" className={className}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-[var(--yellow)]" />
            <h2 className="text-sm font-semibold text-[var(--text)]">
              Edit your profile to get the best results
            </h2>
          </div>
          <p className="mt-1.5 max-w-xl text-sm text-[var(--text-muted)]">
            {completion.reasons?.length
              ? completion.reasons.join(' ')
              : 'The agents search using your own data, so anything missing here narrows what they can find.'}
          </p>
        </div>
        <Button
          href="/individual/profile"
          size="sm"
          icon={completion.has_cv ? <ArrowRight className="h-3.5 w-3.5" /> : <UploadCloud className="h-3.5 w-3.5" />}
        >
          {completion.has_cv ? 'Finish profile' : 'Upload your CV'}
        </Button>
      </div>

      <ProgressBar
        className="mt-5"
        value={completion.percent}
        label={`Profile completeness (${completion.threshold}% needed to run the agents)`}
        showValue
        autoTone
      />

      {missing.length > 0 && (
        <ul className="mt-5 grid gap-2 sm:grid-cols-2">
          {missing.map((field) => (
            <li
              key={field.key}
              className="flex items-start gap-2.5 rounded-xl border border-[var(--border)] bg-[var(--glass-subtle-bg)] px-3 py-2.5"
            >
              <span
                aria-hidden
                className={cx(
                  'mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full',
                  blocking.has(field.key) ? 'bg-[var(--red)]' : 'bg-[var(--text-muted)]'
                )}
              />
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-[var(--text)]">{field.label}</span>
                  {blocking.has(field.key) && (
                    <Badge tone="danger" className="text-[10px]">
                      Required
                    </Badge>
                  )}
                  {field.partially_complete && (
                    <Badge tone="warning" className="text-[10px]">
                      Partial
                    </Badge>
                  )}
                </div>
                {field.hint && (
                  <p className="mt-0.5 text-[11px] leading-snug text-[var(--text-muted)]">
                    {field.hint}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
