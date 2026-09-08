import { ReactNode } from 'react';
import Card from './Card';
import { cx } from './cx';

export interface StatTileProps {
  label: string;
  /**
   * The number/text to show. `null` or `undefined` renders an em dash - a tile
   * must never invent a value it was not given.
   */
  value: ReactNode;
  hint?: string;
  icon?: ReactNode;
  /** Small delta or context line, e.g. "3 new today". */
  trend?: string;
  tone?: 'neutral' | 'accent' | 'success' | 'warning';
  loading?: boolean;
  className?: string;
}

const ICON_TONES = {
  neutral: 'text-[var(--text-muted)] bg-[var(--glass-hover-bg)]',
  accent: 'text-[var(--accent)] bg-[var(--accent-light)]',
  success: 'text-[var(--green)] bg-[var(--glass-hover-bg)]',
  warning: 'text-[var(--yellow)] bg-[var(--glass-hover-bg)]',
} as const;

export function StatTile({
  label,
  value,
  hint,
  icon,
  trend,
  tone = 'neutral',
  loading = false,
  className,
}: StatTileProps) {
  const empty = value === null || value === undefined || value === '';

  return (
    <Card tone="subtle" padding="md" className={cx('flex items-start gap-4', className)}>
      {icon && (
        <span
          aria-hidden
          className={cx(
            'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl',
            ICON_TONES[tone]
          )}
        >
          {icon}
        </span>
      )}
      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-medium uppercase tracking-wider text-[var(--text-muted)]">
          {label}
        </p>
        {loading ? (
          <span className="mt-2 block h-7 w-20 rounded-md skeleton-shimmer" />
        ) : (
          <p
            className={cx(
              'mt-1 text-2xl font-semibold tabular-nums',
              empty ? 'text-[var(--text-muted)]' : 'text-[var(--text)]'
            )}
            title={empty ? 'Not measured yet' : undefined}
          >
            {empty ? '—' : value}
          </p>
        )}
        {trend && !loading && (
          <p className="mt-1 text-xs text-[var(--text-muted)]">{trend}</p>
        )}
        {hint && <p className="mt-1 text-xs text-[var(--text-muted)]">{hint}</p>}
      </div>
    </Card>
  );
}

export default StatTile;
