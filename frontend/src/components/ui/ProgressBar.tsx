import { cx } from './cx';

export type ProgressTone = 'accent' | 'success' | 'warning' | 'info';

const FILL: Record<ProgressTone, string> = {
  accent: 'bg-[var(--accent)]',
  success: 'bg-[var(--green)]',
  warning: 'bg-[var(--yellow)]',
  info: 'bg-[var(--blue)]',
};

export interface ProgressBarProps {
  /** 0-100. Values outside the range are clamped rather than overflowing. */
  value: number;
  label?: string;
  /** Shows the numeric value on the right of the label row. */
  showValue?: boolean;
  suffix?: string;
  tone?: ProgressTone;
  /** Colour by value: red under 50, amber under 80, green at/above 80. */
  autoTone?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}

export function toneForScore(value: number): ProgressTone {
  if (value >= 80) return 'success';
  if (value >= 50) return 'warning';
  return 'accent';
}

export function ProgressBar({
  value,
  label,
  showValue = false,
  suffix = '%',
  tone = 'accent',
  autoTone = false,
  size = 'md',
  className,
}: ProgressBarProps) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  const resolved = autoTone ? toneForScore(pct) : tone;

  return (
    <div className={className}>
      {(label || showValue) && (
        <div className="mb-1.5 flex items-center justify-between gap-2 text-xs">
          {label && <span className="text-[var(--text-muted)]">{label}</span>}
          {showValue && (
            <span className="font-semibold tabular-nums text-[var(--text)]">
              {pct}
              {suffix}
            </span>
          )}
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
        className={cx(
          'w-full overflow-hidden rounded-full bg-[var(--track)]',
          size === 'sm' ? 'h-1' : 'h-2'
        )}
      >
        <div
          className={cx('h-full rounded-full transition-all duration-700', FILL[resolved])}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default ProgressBar;
