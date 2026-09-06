import type { ReactNode } from 'react';

/**
 * A bordered region.
 *
 * Panels are ruled, not floated. No shadow, no radius beyond 2px, no gap-and-
 * lift card treatment -- borders carry the structure the way they do on a
 * printed form. Shadow is reserved for genuinely floating layers: modals and
 * dropdowns.
 */
export function Panel({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`border border-rule bg-surface ${className}`}>{children}</div>
  );
}

/**
 * A panel header: a title on the left, a title block or actions on the right.
 * The right slot is where the format number sits, positioned like the corner of
 * a drawing.
 */
export function PanelHead({
  title,
  right,
  className = '',
}: {
  title: ReactNode;
  right?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex items-center justify-between gap-4 border-b border-rule bg-paper px-3 py-2 ${className}`}
    >
      <h2 className="font-cond text-base font-semibold uppercase tracking-label text-ink">
        {title}
      </h2>
      {right && <div className="flex items-center gap-2">{right}</div>}
    </div>
  );
}

/**
 * A screen header.
 *
 * Information hierarchy, in the order an inspector needs it: which package,
 * then whether it is clean. Those two answers come before anything else on the
 * screen and before any scrolling.
 */
export function ScreenHead({
  eyebrow,
  title,
  right,
  children,
}: {
  eyebrow?: string;
  title: ReactNode;
  right?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <header className="border-b border-rule-strong bg-surface px-6 py-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          {eyebrow && <div className="label mb-1">{eyebrow}</div>}
          <div className="font-cond text-xl font-semibold leading-none text-ink">
            {title}
          </div>
        </div>
        {right && <div className="flex flex-wrap items-center gap-3">{right}</div>}
      </div>
      {children && <div className="mt-3">{children}</div>}
    </header>
  );
}

/**
 * An empty state.
 *
 * No illustration, no cartoon inspector, no isometric factory. A clean package
 * is a positive result and should read as one -- a stamp mark and a plain line,
 * not an absence.
 */
export function EmptyState({
  mark,
  headline,
  children,
}: {
  mark?: ReactNode;
  headline: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-14 text-center">
      {mark}
      <div className="font-cond text-lg font-semibold text-ink">{headline}</div>
      {children && (
        <p className="max-w-[46ch] font-sans text-sm text-graphite">{children}</p>
      )}
    </div>
  );
}

/**
 * A failure message.
 *
 * The `kind` distinction is load-bearing and comes straight from the backend's
 * own discipline: an unreadable scan is a fact about the *document* and the
 * answer is REVIEW; a provider outage is a fact about the *system* and the
 * answer is retry. The user needs to know which, so the two never share
 * wording or colour.
 */
export function Problem({
  kind,
  headline,
  children,
}: {
  kind: 'document' | 'system';
  headline: string;
  children?: ReactNode;
}) {
  const style =
    kind === 'document'
      ? 'border-pencil bg-pencil-soft'
      : 'border-rule-strong bg-paper';
  return (
    <div className={`border-l-3 border px-4 py-3 ${style}`}>
      <div className="label mb-1">
        {kind === 'document' ? 'Document problem' : 'System problem'}
      </div>
      <div className="font-sans text-sm font-medium text-ink">{headline}</div>
      {children && (
        <p className="mt-1 max-w-[62ch] font-sans text-sm text-graphite">{children}</p>
      )}
    </div>
  );
}
