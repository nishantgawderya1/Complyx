import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { WORKLIST } from '@/lib/fixtures';
import type { PackageStatus, Severity } from '@/lib/types';
import { Mono } from '@/components/primitives/Text';
import { FindingSummary, StatusTag } from '@/components/primitives/Tags';
import { DocSquares } from '@/components/primitives/DocSquares';
import { ScreenHead } from '@/components/primitives/Panel';

/**
 * Package worklist — the home screen and the most-used view in the product.
 *
 * A dense ruled table, scannable at forty rows without scrolling on a laptop.
 * Rows with critical findings carry a red left rule; rows awaiting confirmation
 * carry ochre. That rule is the only decoration, and it encodes state.
 *
 * Filters are checkboxes on a ruled list, not pills. Pills imply a fluid,
 * exploratory search; this is a work queue and the filters are a standing
 * configuration an inspector sets once for a shift.
 */

const STATUSES: PackageStatus[] = ['incomplete', 'processing', 'review', 'complete'];
const SEVERITIES: Severity[] = ['CRITICAL', 'MAJOR', 'MINOR'];

export function Worklist() {
  const [statuses, setStatuses] = useState<Set<PackageStatus>>(new Set());
  const [severities, setSeverities] = useState<Set<Severity>>(new Set());

  const rows = useMemo(() => {
    return WORKLIST.filter((pkg) => {
      if (statuses.size && !statuses.has(pkg.status)) return false;
      if (severities.size) {
        const present = new Set(pkg.findings.map((f) => f.severity));
        if (![...severities].some((s) => present.has(s))) return false;
      }
      return true;
    });
  }, [statuses, severities]);

  function toggle<T>(set: Set<T>, value: T, apply: (next: Set<T>) => void) {
    const next = new Set(set);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    apply(next);
  }

  return (
    <>
      <ScreenHead
        eyebrow="GHAVP-1&2 Main Plant · NPCIL · Tata Projects Ltd."
        title="Package worklist"
        right={
          <Link
            to="/intake"
            className="border border-blueprint bg-blueprint px-3 py-1.5 font-sans text-sm font-medium text-white hover:bg-[#163F63]"
          >
            New package
          </Link>
        }
      />

      <div className="flex min-h-0 flex-1 overflow-hidden">
        {/* ---- filter rail ---- */}
        <aside className="w-[172px] shrink-0 overflow-y-auto border-r border-rule bg-paper px-4 py-4">
          <FilterGroup heading="Status">
            {STATUSES.map((status) => (
              <FilterCheck
                key={status}
                label={status}
                checked={statuses.has(status)}
                onChange={() => toggle(statuses, status, setStatuses)}
              />
            ))}
          </FilterGroup>

          <FilterGroup heading="Finding severity">
            {SEVERITIES.map((severity) => (
              <FilterCheck
                key={severity}
                label={severity.toLowerCase()}
                checked={severities.has(severity)}
                onChange={() => toggle(severities, severity, setSeverities)}
              />
            ))}
          </FilterGroup>

          {(statuses.size > 0 || severities.size > 0) && (
            <button
              type="button"
              onClick={() => {
                setStatuses(new Set());
                setSeverities(new Set());
              }}
              className="mt-2 font-sans text-xs text-blueprint underline"
            >
              Clear filters
            </button>
          )}
        </aside>

        {/* ---- the table ---- */}
        <div className="min-w-0 flex-1 overflow-auto">
          <table className="ruled">
            <thead>
              <tr>
                <th>Coupon</th>
                <th>Welder</th>
                <th>WPS</th>
                <th>Test date</th>
                <th>Documents</th>
                <th>Findings</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((pkg) => {
                const counts = {
                  critical: pkg.findings.filter((f) => f.severity === 'CRITICAL').length,
                  major: pkg.findings.filter((f) => f.severity === 'MAJOR').length,
                  minor: pkg.findings.filter((f) => f.severity === 'MINOR').length,
                };
                const rule =
                  counts.critical > 0
                    ? 'border-l-redpen'
                    : pkg.status === 'review' || counts.major > 0
                      ? 'border-l-pencil'
                      : 'border-l-transparent';

                return (
                  <tr key={pkg.id} className={`border-l-2 ${rule}`}>
                    <td>
                      <Link
                        to={`/package/${pkg.id}`}
                        className="font-mono text-sm font-medium text-blueprint hover:underline"
                      >
                        {pkg.coupon_no}
                      </Link>
                    </td>
                    <td>
                      <div className="font-sans text-sm text-ink">{pkg.welder_name}</div>
                      <Mono size="2xs" muted>
                        {pkg.welder_id}
                      </Mono>
                    </td>
                    <td>
                      <Mono size="xs" muted>
                        {pkg.wps_no}
                      </Mono>
                    </td>
                    <td>
                      {pkg.test_date ? (
                        <Mono size="xs">{pkg.test_date}</Mono>
                      ) : (
                        <span className="font-mono text-xs text-graphite">—</span>
                      )}
                    </td>
                    <td>
                      <DocSquares present={pkg.documents.map((d) => d.doc_type)} />
                    </td>
                    <td>
                      <FindingSummary {...counts} />
                    </td>
                    <td>
                      <StatusTag status={pkg.status} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {rows.length === 0 && (
            <div className="px-6 py-12 text-center">
              <div className="font-cond text-lg font-semibold text-ink">
                No packages match these filters
              </div>
              <p className="mt-1 font-sans text-sm text-graphite">
                Clear one or more filters to widen the queue.
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function FilterGroup({
  heading,
  children,
}: {
  heading: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-5">
      <div className="label mb-1.5 border-b border-rule pb-1">{heading}</div>
      <div className="flex flex-col gap-1">{children}</div>
    </div>
  );
}

function FilterCheck({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 font-sans text-sm capitalize text-graphite hover:text-ink">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="h-3 w-3 accent-blueprint"
      />
      {label}
    </label>
  );
}
