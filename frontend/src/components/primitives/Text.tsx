import type { ReactNode } from 'react';

/**
 * Typographic primitives.
 *
 * `Mono` exists so the monospace rule is enforced by import rather than by
 * memory. Every value, ID, code, date and measurement goes through it.
 * Monospace makes character-level differences visible, and TPL/GHAVP/W-71
 * versus TPL/GHAVP/W-72 is exactly the kind of difference this product exists
 * to catch. If you find yourself typing `font-mono` by hand, use this instead.
 */

interface MonoProps {
  children: ReactNode;
  /** Sets the value in red. Findings only -- never for emphasis. */
  finding?: boolean;
  /** Dims the value. For "not stated" and inherited context. */
  muted?: boolean;
  size?: '2xs' | 'xs' | 'sm' | 'base' | 'lg';
  className?: string;
  title?: string;
}

const SIZE: Record<NonNullable<MonoProps['size']>, string> = {
  '2xs': 'text-2xs',
  xs: 'text-xs',
  sm: 'text-sm',
  base: 'text-base',
  lg: 'text-lg',
};

export function Mono({
  children,
  finding = false,
  muted = false,
  size = 'sm',
  className = '',
  title,
}: MonoProps) {
  const tone = finding ? 'text-redpen' : muted ? 'text-graphite' : 'text-ink';
  return (
    <span className={`font-mono ${SIZE[size]} ${tone} ${className}`} title={title}>
      {children}
    </span>
  );
}

/**
 * A value the system could not read.
 *
 * Rendered as an explicit mark rather than an empty cell, because a blank cell
 * reads as "nothing to see" and this is the opposite: it is the system saying
 * it does not know.
 */
export function NotRead({ reason }: { reason?: string }) {
  return (
    <span
      className="font-mono text-xs text-pencil"
      title={reason ?? 'Not read from this document'}
    >
      — not read
    </span>
  );
}

/**
 * A governing clause reference.
 *
 * Clause references are the product's authority. Their constant presence
 * immediately after any derived value is what tells an inspector this is not a
 * guess, so they are set consistently and never abbreviated away.
 */
export function ClauseRef({ code, className = '' }: { code: string; className?: string }) {
  return (
    <span
      className={`font-mono text-2xs tracking-label text-blueprint ${className}`}
      title={`ASME Section IX ${code}`}
    >
      {code}
    </span>
  );
}

/** Uppercase letterspaced label. Form labels, column heads, metadata keys. */
export function Label({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <span className={`label ${className}`}>{children}</span>;
}

/**
 * A drawing title block.
 *
 * Format numbers are typographic artifacts. Set small, letterspaced and
 * monospace in the corner of a document panel, `NPCIL/QMD/TF-127 Rev.R0` does
 * more for credibility than any illustration.
 */
export function TitleBlock({
  formatNo,
  matched,
  verified,
}: {
  formatNo: string;
  matched?: boolean;
  verified?: boolean;
}) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="titleblock">{formatNo}</span>
      {matched === false && (
        <span className="border border-pencil bg-pencil-soft px-1 font-mono text-2xs uppercase tracking-label text-pencil">
          Template unknown
        </span>
      )}
      {matched !== false && verified === false && (
        <span
          className="border border-pencil bg-pencil-soft px-1 font-mono text-2xs uppercase tracking-label text-pencil"
          title="Template regions have not been checked by a qualified reviewer"
        >
          Unverified
        </span>
      )}
    </span>
  );
}

/** A label/value pair, ruled like a form field rather than floated in a card. */
export function Field({
  label,
  children,
  wide = false,
}: {
  label: string;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <div className={wide ? 'col-span-2' : ''}>
      <div className="label mb-0.5">{label}</div>
      <div className="font-mono text-sm text-ink">{children}</div>
    </div>
  );
}
