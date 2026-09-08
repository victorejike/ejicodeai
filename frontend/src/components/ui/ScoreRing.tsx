import { cx } from './cx';
import { toneForScore } from './ProgressBar';

const STROKE = {
  accent: 'var(--accent)',
  success: 'var(--green)',
  warning: 'var(--yellow)',
  info: 'var(--blue)',
} as const;

export interface ScoreRingProps {
  /** 0-100, or `null` when nothing has been measured yet. */
  value: number | null | undefined;
  size?: number;
  thickness?: number;
  label?: string;
  className?: string;
}

/**
 * Circular score readout used for the ATS score and match scores.
 *
 * An unmeasured score renders as a dash inside an empty ring - not as a zero,
 * which would read as "scored badly".
 */
export function ScoreRing({
  value,
  size = 112,
  thickness = 8,
  label,
  className,
}: ScoreRingProps) {
  const known = typeof value === 'number' && Number.isFinite(value);
  const pct = known ? Math.max(0, Math.min(100, Math.round(value as number))) : 0;
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;
  const dash = (pct / 100) * circumference;
  const stroke = known ? STROKE[toneForScore(pct)] : 'var(--border)';

  return (
    <div
      className={cx('inline-flex flex-col items-center gap-2', className)}
      role="img"
      aria-label={`${label ?? 'Score'}: ${known ? `${pct} out of 100` : 'not measured yet'}`}
    >
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--track)"
            strokeWidth={thickness}
          />
          {known && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={stroke}
              strokeWidth={thickness}
              strokeLinecap="round"
              strokeDasharray={`${dash} ${circumference - dash}`}
              className="transition-all duration-700"
            />
          )}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className={cx(
              'text-2xl font-semibold tabular-nums',
              known ? 'text-[var(--text)]' : 'text-[var(--text-muted)]'
            )}
          >
            {known ? pct : '—'}
          </span>
          {known && <span className="text-[10px] text-[var(--text-muted)]">/ 100</span>}
        </div>
      </div>
      {label && (
        <span className="text-[11px] font-medium uppercase tracking-wider text-[var(--text-muted)]">
          {label}
        </span>
      )}
    </div>
  );
}

export default ScoreRing;
