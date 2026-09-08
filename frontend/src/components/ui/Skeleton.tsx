import { cx } from './cx';

export interface SkeletonProps {
  className?: string;
  /** Convenience for stacked text lines. */
  lines?: number;
  rounded?: 'sm' | 'md' | 'lg' | 'full';
}

const ROUNDED = {
  sm: 'rounded',
  md: 'rounded-lg',
  lg: 'rounded-2xl',
  full: 'rounded-full',
} as const;

/** Loading placeholder. Never renders text, so it cannot be mistaken for data. */
export function Skeleton({ className, lines, rounded = 'md' }: SkeletonProps) {
  if (lines && lines > 1) {
    return (
      <div className="space-y-2" aria-hidden>
        {Array.from({ length: lines }).map((_, i) => (
          <span
            key={i}
            className={cx(
              'block h-3.5 skeleton-shimmer',
              ROUNDED[rounded],
              i === lines - 1 ? 'w-2/3' : 'w-full',
              className
            )}
          />
        ))}
      </div>
    );
  }

  return (
    <span
      aria-hidden
      className={cx('block h-4 w-full skeleton-shimmer', ROUNDED[rounded], className)}
    />
  );
}

export default Skeleton;
