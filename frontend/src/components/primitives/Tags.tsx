import type { PackageStatus, ReadMethod, Severity } from '@/lib/types';

/**
 * Status marks.
 *
 * One rule governs every tag here: **colour never carries meaning alone.**
 * Every tag pairs its colour with a text label, so the interface works for a
 * colour-blind inspector and survives being printed in greyscale and filed --
 * which the package confirmation view will be.
 *
 * Shapes are square. Forms have corners.
 */

const BASE =
  'inline-flex items-center gap-1 border px-1.5 py-px font-mono text-2xs font-medium uppercase tracking-label whitespace-nowrap';

const SEVERITY_STYLE: Record<Severity, string> = {
  CRITICAL: 'border-redpen bg-redpen-soft text-redpen',
  MAJOR: 'border-pencil bg-pencil-soft text-pencil',
  MINOR: 'border-rule-strong bg-paper text-graphite',
};

export function SeverityTag({ severity }: { severity: Severity }) {
  return <span className={`${BASE} ${SEVERITY_STYLE[severity]}`}>{severity}</span>;
}

const STATUS_STYLE: Record<PackageStatus, string> = {
  incomplete: 'border-pencil bg-pencil-soft text-pencil',
  processing: 'border-blueprint bg-blueprint-soft text-blueprint',
  review: 'border-redpen bg-redpen-soft text-redpen',
  complete: 'border-stamp bg-stamp-soft text-stamp',
};

const STATUS_LABEL: Record<PackageStatus, string> = {
  incomplete: 'Incomplete',
  processing: 'Processing',
  review: 'Review',
  complete: 'Complete',
};

export function StatusTag({ status }: { status: PackageStatus }) {
  return <span className={`${BASE} ${STATUS_STYLE[status]}`}>{STATUS_LABEL[status]}</span>;
}

/**
 * How a value was read, and how firmly.
 *
 * Shown on the extraction overlay and in finding detail rather than hidden in a
 * log. A value recovered from a fallback rectangle is materially less
 * trustworthy than one located by its anchor, and the reviewer deciding whether
 * to trust it needs that on screen.
 */
const READ_METHOD_LABEL: Record<ReadMethod, string> = {
  template_region: 'Anchored',
  template_region_fallback: 'Fallback region',
  full_page: 'Whole page',
  checkbox_cv: 'CV only',
  checkbox_vision: 'Vision only',
  checkbox_agreed: 'Both readers agree',
};

export function ReadMethodTag({
  method,
  confidence,
}: {
  method: ReadMethod;
  confidence: number;
}) {
  const degraded = method !== 'template_region' && method !== 'checkbox_agreed';
  const style = degraded
    ? 'border-pencil bg-pencil-soft text-pencil'
    : 'border-rule-strong bg-paper text-graphite';
  return (
    <span className={`${BASE} ${style}`}>
      {READ_METHOD_LABEL[method]}
      <span className="opacity-60">{confidence.toFixed(2)}</span>
    </span>
  );
}

/**
 * An unverified rule table entry or template.
 *
 * DESIGN.md §12: never let the interface look more certain than the system is.
 * An unverified rule backing a derived value must be as visible as a finding.
 */
export function UnverifiedMark({ what = 'Rule' }: { what?: string }) {
  return (
    <span
      className={`${BASE} border-pencil bg-pencil-soft text-pencil`}
      title={`This ${what.toLowerCase()} has not been checked by a qualified reviewer and must not back a verdict shown to an inspector`}
    >
      {what} unverified
    </span>
  );
}

/** A clean result. Reads as a positive outcome, not as an absence. */
export function ClearMark({ children = 'No findings' }: { children?: string }) {
  return (
    <span className={`${BASE} border-stamp bg-stamp-soft text-stamp`}>{children}</span>
  );
}

/**
 * Findings summary for a dense table row: counts by severity, or a clear mark.
 */
export function FindingSummary({
  critical,
  major,
  minor,
}: {
  critical: number;
  major: number;
  minor: number;
}) {
  if (critical + major + minor === 0) return <ClearMark />;
  return (
    <span className="inline-flex items-center gap-1.5">
      {critical > 0 && (
        <span className="font-mono text-xs font-medium text-redpen">
          {critical} critical
        </span>
      )}
      {major > 0 && (
        <span className="font-mono text-xs text-pencil">{major} major</span>
      )}
      {minor > 0 && (
        <span className="font-mono text-xs text-graphite">{minor} minor</span>
      )}
    </span>
  );
}
