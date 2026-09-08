import { ReactNode } from 'react';
import { cx } from './cx';

export interface EmptyStateProps {
  title: string;
  /** Say what is actually missing and what to do next - never "no data". */
  description?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cx(
        'flex flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--border)] px-6 py-12 text-center',
        className
      )}
    >
      {icon && (
        <span
          aria-hidden
          className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--glass-hover-bg)] text-[var(--text-muted)]"
        >
          {icon}
        </span>
      )}
      <h3 className="text-sm font-semibold text-[var(--text)]">{title}</h3>
      {description && (
        <p className="mt-1.5 max-w-md text-sm text-[var(--text-muted)]">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export default EmptyState;
