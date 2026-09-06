import type { ButtonHTMLAttributes, ReactNode } from 'react';

/**
 * Buttons.
 *
 * Background darkens on hover; 1px inset on press. Nothing moves position,
 * nothing lifts, nothing scales. Motion here is functional or absent.
 *
 * Note what is missing: there is no destructive/danger variant in red. Red is
 * reserved for findings. A dismiss action is a neutral button with a required
 * reason, not a red one -- dismissing a finding is a considered judgement, not
 * a dangerous act, and colouring it as danger would both misdescribe it and
 * dilute the one signal that matters.
 */

type Variant = 'primary' | 'default' | 'quiet';

const VARIANT: Record<Variant, string> = {
  primary:
    'border-blueprint bg-blueprint text-white hover:bg-[#163F63] active:translate-y-px',
  default:
    'border-rule-strong bg-surface text-ink hover:bg-paper active:translate-y-px',
  quiet:
    'border-transparent bg-transparent text-graphite hover:bg-paper hover:text-ink active:translate-y-px',
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  children: ReactNode;
  /** Keyboard shortcut hint, shown right-aligned. Inspectors do not use mice. */
  shortcut?: string;
}

export function Button({
  variant = 'default',
  children,
  shortcut,
  className = '',
  ...rest
}: ButtonProps) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-2 border px-3 py-1.5 font-sans text-sm font-medium transition-colors duration-120 disabled:cursor-not-allowed disabled:opacity-40 ${VARIANT[variant]} ${className}`}
      {...rest}
    >
      {children}
      {shortcut && (
        <kbd className="border border-current px-1 font-mono text-2xs opacity-60">
          {shortcut}
        </kbd>
      )}
    </button>
  );
}

/**
 * The sign-off action.
 *
 * Deliberately heavier than a normal button. This is the moment a human takes
 * responsibility for a qualification record, and it should not feel like
 * clicking "save".
 */
export function SignOffButton({
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { children: ReactNode }) {
  return (
    <button
      type="button"
      className="inline-flex items-center justify-center border-2 border-stamp bg-stamp px-6 py-2.5 font-cond text-base font-semibold uppercase tracking-label text-white transition-colors duration-120 hover:bg-[#245741] active:translate-y-px disabled:cursor-not-allowed disabled:border-rule-strong disabled:bg-rule disabled:text-graphite"
      {...rest}
    >
      {children}
    </button>
  );
}
