import { ReactNode } from 'react';
import { cx } from './cx';

export type AlertTone = 'info' | 'success' | 'warning' | 'danger';

const TONES: Record<AlertTone, string> = {
  info: 'border-[color:color-mix(in_srgb,var(--blue)_35%,transparent)] bg-[color:color-mix(in_srgb,var(--blue)_10%,transparent)]',
  success:
    'border-[color:color-mix(in_srgb,var(--green)_35%,transparent)] bg-[color:color-mix(in_srgb,var(--green)_10%,transparent)]',
  warning:
    'border-[color:color-mix(in_srgb,var(--yellow)_35%,transparent)] bg-[color:color-mix(in_srgb,var(--yellow)_10%,transparent)]',
  danger: 'border-[var(--border-red)] bg-[var(--accent-light)]',
};

const ICON_COLOR: Record<AlertTone, string> = {
  info: 'text-[var(--blue)]',
  success: 'text-[var(--green)]',
  warning: 'text-[var(--yellow)]',
  danger: 'text-[var(--red)]',
};

export interface AlertProps {
  tone?: AlertTone;
  title?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  children?: ReactNode;
  className?: string;
}

/** Inline message: errors from a call, gate explanations, degraded-mode notices. */
export function Alert({
  tone = 'info',
  title,
  icon,
  action,
  children,
  className,
}: AlertProps) {
  return (
    <div
      role={tone === 'danger' ? 'alert' : 'status'}
      className={cx('flex gap-3 rounded-2xl border px-4 py-3 text-sm', TONES[tone], className)}
    >
      {icon && (
        <span aria-hidden className={cx('mt-0.5 shrink-0', ICON_COLOR[tone])}>
          {icon}
        </span>
      )}
      <div className="min-w-0 flex-1">
        {title && <p className="font-semibold text-[var(--text)]">{title}</p>}
        {children && (
          <div className={cx('text-[var(--text-muted)]', title ? 'mt-1' : undefined)}>{children}</div>
        )}
      </div>
      {action && <div className="shrink-0 self-center">{action}</div>}
    </div>
  );
}

export default Alert;
