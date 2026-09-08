import { ReactNode } from 'react';
import { cx } from './cx';

export interface SectionHeaderProps {
  title: string;
  description?: string;
  /** Right-aligned controls: filters, "view all", a small button. */
  actions?: ReactNode;
  icon?: ReactNode;
  className?: string;
}

/** Heading row used above every list, table and chart block. */
export function SectionHeader({
  title,
  description,
  actions,
  icon,
  className,
}: SectionHeaderProps) {
  return (
    <div
      className={cx(
        'mb-4 flex flex-wrap items-start justify-between gap-3',
        className
      )}
    >
      <div className="flex items-start gap-3">
        {icon && (
          <span aria-hidden className="mt-0.5 text-[var(--accent)]">
            {icon}
          </span>
        )}
        <div>
          <h2 className="text-base font-semibold text-[var(--text)]">{title}</h2>
          {description && (
            <p className="mt-0.5 text-sm text-[var(--text-muted)]">{description}</p>
          )}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export default SectionHeader;
