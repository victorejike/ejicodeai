/**
 * The shared UI kit.
 *
 * Import from `@/components/ui` (or a relative path) and nothing else - every
 * surface, button, badge and table in the app is defined here exactly once, on
 * top of the `.apple-*` utilities in `globals.css`. Pages should not hand-roll
 * their own glass panels: that is what made three dashboards look like three
 * different products.
 */
export { cx } from './cx';
export type { ClassValue } from './cx';

export { AppShell } from './AppShell';
export type { AppShellProps } from './AppShell';

export { Alert } from './Alert';
export type { AlertProps, AlertTone } from './Alert';

export { Badge } from './Badge';
export type { BadgeProps, BadgeTone } from './Badge';

export { Button } from './Button';
export type { ButtonProps, ButtonSize, ButtonVariant } from './Button';

export { Card } from './Card';
export type { CardPadding, CardProps, CardTone } from './Card';

export { EmptyState } from './EmptyState';
export type { EmptyStateProps } from './EmptyState';

export { Modal } from './Modal';
export type { ModalProps } from './Modal';

export { PageHeader } from './PageHeader';
export type { PageHeaderProps } from './PageHeader';

export { ProgressBar, toneForScore } from './ProgressBar';
export type { ProgressBarProps, ProgressTone } from './ProgressBar';

export { ScoreRing } from './ScoreRing';
export type { ScoreRingProps } from './ScoreRing';

export { SectionHeader } from './SectionHeader';
export type { SectionHeaderProps } from './SectionHeader';

export { Skeleton } from './Skeleton';
export type { SkeletonProps } from './Skeleton';

export { StatTile } from './StatTile';
export type { StatTileProps } from './StatTile';

export { Table } from './Table';
export type { Column, TableProps } from './Table';
