'use client';

import Link from 'next/link';
import { ButtonHTMLAttributes, ReactNode } from 'react';
import { cx } from './cx';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

const VARIANTS: Record<ButtonVariant, string> = {
  primary: 'apple-button-primary',
  secondary: 'apple-button-secondary',
  ghost:
    'rounded-full border border-transparent text-[var(--text-muted)] hover:text-[var(--text)] hover:border-[var(--border)] transition-colors',
  danger:
    'rounded-full bg-[var(--accent)] text-white font-semibold transition-all duration-300 hover:bg-[var(--accent-hover)]',
};

const SIZES: Record<ButtonSize, string> = {
  sm: 'px-3.5 py-1.5 text-xs',
  md: 'px-5 py-2.5 text-sm',
  lg: 'px-7 py-3 text-base',
};

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'disabled'> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Renders a Next link styled as a button. */
  href?: string;
  loading?: boolean;
  disabled?: boolean;
  /**
   * Why the button cannot be used right now. Shows as the native tooltip and
   * implies `disabled` - the profile gate needs a visibly-unavailable button
   * that explains itself, not a hidden one.
   */
  disabledReason?: string;
  icon?: ReactNode;
  fullWidth?: boolean;
  children?: ReactNode;
}

export function Button({
  variant = 'primary',
  size = 'md',
  href,
  loading = false,
  disabled = false,
  disabledReason,
  icon,
  fullWidth = false,
  className,
  children,
  ...rest
}: ButtonProps) {
  const isDisabled = disabled || loading || Boolean(disabledReason);
  const classes = cx(
    'inline-flex items-center justify-center gap-2 whitespace-nowrap',
    VARIANTS[variant],
    SIZES[size],
    fullWidth && 'w-full',
    className
  );

  const inner = (
    <>
      {loading ? (
        <span
          aria-hidden
          className="h-3.5 w-3.5 rounded-full border-2 border-current border-t-transparent animate-spin"
        />
      ) : (
        icon
      )}
      {children}
    </>
  );

  if (href && !isDisabled) {
    return (
      <Link href={href} className={classes} title={rest.title}>
        {inner}
      </Link>
    );
  }

  return (
    <button
      type={rest.type ?? 'button'}
      className={classes}
      disabled={isDisabled}
      aria-disabled={isDisabled || undefined}
      title={disabledReason ?? rest.title}
      {...rest}
    >
      {inner}
    </button>
  );
}

export default Button;
