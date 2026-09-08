import { ReactNode } from 'react';
import PageHeader, { PageHeaderProps } from './PageHeader';
import { cx } from './cx';

export interface AppShellProps extends Omit<PageHeaderProps, 'children' | 'className'> {
  /** Rendered inside the page header, under the description (gates, banners). */
  banner?: ReactNode;
  /** Constrains the content column. `wide` suits dashboards, `narrow` suits forms. */
  width?: 'narrow' | 'default' | 'wide' | 'full';
  children?: ReactNode;
  className?: string;
}

const WIDTHS = {
  narrow: 'max-w-3xl',
  default: 'max-w-5xl',
  wide: 'max-w-7xl',
  full: 'max-w-none',
} as const;

/**
 * The page template. Every page renders `<AppShell title=... >` so the header,
 * the content width and the vertical rhythm are identical across the app - the
 * chrome (sidebar, top bar, ambient background) comes from the root layout.
 */
export function AppShell({
  banner,
  width = 'wide',
  children,
  className,
  ...header
}: AppShellProps) {
  return (
    <div className={cx('mx-auto w-full', WIDTHS[width], className)}>
      <PageHeader {...header}>{banner}</PageHeader>
      <div className="space-y-8 pb-12">{children}</div>
    </div>
  );
}

export default AppShell;
