import { ElementType, HTMLAttributes, ReactNode } from 'react';
import { cx } from './cx';

export type CardTone = 'glass' | 'subtle' | 'solid';
export type CardPadding = 'none' | 'sm' | 'md' | 'lg';

const TONES: Record<CardTone, string> = {
  glass: 'apple-glass',
  subtle: 'apple-glass-subtle',
  solid: 'bg-[var(--card)] border border-[var(--border)]',
};

const PADDING: Record<CardPadding, string> = {
  none: '',
  sm: 'p-4',
  md: 'p-5',
  lg: 'p-7',
};

export interface CardProps extends HTMLAttributes<HTMLElement> {
  tone?: CardTone;
  padding?: CardPadding;
  /** Renders as a different element (e.g. `section`, `li`, `article`). */
  as?: ElementType;
  /** Adds the lift-on-hover treatment used by clickable cards. */
  interactive?: boolean;
  children?: ReactNode;
}

/**
 * The one card surface in the app. Wraps the `.apple-glass*` utilities so the
 * blur, border and shadow are defined once in `globals.css` instead of being
 * re-typed per page.
 */
export function Card({
  tone = 'glass',
  padding = 'md',
  as: Tag = 'div',
  interactive = false,
  className,
  children,
  ...rest
}: CardProps) {
  return (
    <Tag
      className={cx(
        'rounded-2xl',
        TONES[tone],
        PADDING[padding],
        interactive &&
          'transition-all duration-300 hover:border-[var(--border-red)] hover:-translate-y-0.5 cursor-pointer',
        className
      )}
      {...rest}
    >
      {children}
    </Tag>
  );
}

export default Card;
