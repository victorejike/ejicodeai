import { HTMLAttributes, ReactNode } from 'react';
import { cx } from './cx';

export type BadgeTone =
  | 'neutral'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'accent'
  | 'unknown';

const TONES: Record<BadgeTone, string> = {
  neutral: 'text-[var(--text-muted)] border-[var(--border)] bg-[var(--glass-subtle-bg)]',
  success: 'text-[var(--green)] border-[color:color-mix(in_srgb,var(--green)_35%,transparent)] bg-[color:color-mix(in_srgb,var(--green)_12%,transparent)]',
  warning: 'text-[var(--yellow)] border-[color:color-mix(in_srgb,var(--yellow)_35%,transparent)] bg-[color:color-mix(in_srgb,var(--yellow)_12%,transparent)]',
  danger: 'text-[var(--red)] border-[var(--border-red)] bg-[var(--accent-light)]',
  info: 'text-[var(--blue)] border-[color:color-mix(in_srgb,var(--blue)_35%,transparent)] bg-[color:color-mix(in_srgb,var(--blue)_12%,transparent)]',
  accent: 'text-[var(--accent)] border-[var(--border-red)] bg-[var(--accent-light)]',
  /** For values the backend genuinely does not know yet. */
  unknown: 'text-[var(--text-muted)] border-dashed border-[var(--border)] bg-transparent',
};

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  /** Small leading dot, for live/status pills. */
  dot?: boolean;
  pulse?: boolean;
  children?: ReactNode;
}

export function Badge({
  tone = 'neutral',
  dot = false,
  pulse = false,
  className,
  children,
  ...rest
}: BadgeProps) {
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium leading-5',
        TONES[tone],
        className
      )}
      {...rest}
    >
      {dot && (
        <span
          aria-hidden
          className={cx('h-1.5 w-1.5 rounded-full bg-current', pulse && 'animate-pulse-soft')}
        />
      )}
      {children}
    </span>
  );
}

export default Badge;
