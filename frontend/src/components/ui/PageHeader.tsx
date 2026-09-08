import { ReactNode } from 'react';
import { cx } from './cx';

export interface PageHeaderProps {
  /** Small line above the title, e.g. "Individual". */
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  /** Rendered under the description - completion cards, warnings, gates. */
  children?: ReactNode;
  className?: string;
}

/**
 * The top of every page: one eyebrow, one title, one description, actions on
 * the right. Using this everywhere is what makes the pages look like one app.
 */
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  children,
  className,
}: PageHeaderProps) {
  return (
    <header className={cx('mb-8', className)}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          {eyebrow && (
            <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--accent)]">
              {eyebrow}
            </p>
          )}
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text)] sm:text-3xl">
            {title}
          </h1>
          {description && (
            <p className="mt-2 max-w-2xl text-sm text-[var(--text-muted)]">{description}</p>
          )}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {children && <div className="mt-6">{children}</div>}
    </header>
  );
}

export default PageHeader;
