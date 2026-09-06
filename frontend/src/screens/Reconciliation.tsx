import { RECONCILIATION } from '@/lib/fixtures';
import { DOC_LABEL, DOC_ORDER } from '@/lib/types';
import { Mono } from '@/components/primitives/Text';

/**
 * Reconciliation grid.
 *
 * For cross-document findings a comparison grid is clearer than a list. Rows
 * are fields, columns are the six documents, cells hold the value each document
 * states.
 *
 * The design does the work: **agreement reads as a clean row**, so a
 * disagreement is visible because one cell breaks the pattern — before anyone
 * reads a word. Agreeing values are set in graphite; the odd one out is red and
 * boxed. An inspector scanning this grid finds the discrepancy in about a
 * second, which is the whole argument for the screen.
 *
 * The field column is frozen so the grid stays readable when it scrolls
 * horizontally on a tablet.
 */
export function Reconciliation({
  onOpenFinding,
}: {
  onOpenFinding?: (findingId: string) => void;
}) {
  return (
    <div className="p-6">
      <div className="mb-3 max-w-[70ch]">
        <h2 className="font-cond text-lg font-semibold text-ink">
          Field agreement across the package
        </h2>
        <p className="mt-1 font-sans text-sm text-graphite">
          Each row is one field as every document states it. A row where all
          present values agree needs no attention. A cell that breaks its row is
          the finding.
        </p>
      </div>

      <div className="overflow-x-auto border border-rule bg-surface">
        <table className="ruled min-w-[900px]">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-paper">Field</th>
              {DOC_ORDER.map((doc) => (
                <th key={doc}>{DOC_LABEL[doc]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {RECONCILIATION.map((row) => (
              <tr
                key={row.field_name}
                className={`border-l-2 ${
                  row.agrees ? 'border-l-transparent' : 'border-l-redpen'
                }`}
              >
                <th
                  scope="row"
                  className="sticky left-0 z-10 border-b border-rule bg-surface px-3 py-2 text-left align-top"
                >
                  <div className="font-sans text-sm font-medium text-ink">
                    {row.label}
                  </div>
                  {!row.agrees && row.finding_id && onOpenFinding && (
                    <button
                      type="button"
                      onClick={() => onOpenFinding(row.finding_id!)}
                      className="mt-0.5 font-mono text-2xs text-blueprint underline"
                    >
                      open finding
                    </button>
                  )}
                </th>

                {DOC_ORDER.map((doc) => {
                  const value = row.values[doc];

                  // Absent from this document is not a disagreement. Not every
                  // form carries every field, and marking that red would train
                  // inspectors to ignore red.
                  if (value === undefined || value === null) {
                    return (
                      <td key={doc} className="text-center">
                        <span className="font-mono text-xs text-rule-strong">·</span>
                      </td>
                    );
                  }

                  // The odd one out: the value that differs from the majority.
                  const present = DOC_ORDER.map((d) => row.values[d]).filter(
                    (v): v is string => typeof v === 'string',
                  );
                  const counts = new Map<string, number>();
                  present.forEach((v) => counts.set(v, (counts.get(v) ?? 0) + 1));
                  const majority = [...counts.entries()].sort((a, b) => b[1] - a[1])[0][0];
                  const odd = !row.agrees && value !== majority;

                  return (
                    <td key={doc}>
                      {odd ? (
                        <span className="inline-block border border-redpen bg-redpen-soft px-1.5 py-px">
                          <Mono size="xs" finding>
                            {value}
                          </Mono>
                        </span>
                      ) : (
                        <Mono size="xs" muted>
                          {value}
                        </Mono>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-3 max-w-[70ch] font-sans text-xs text-graphite">
        A dot means the document does not carry that field. Absence is not
        disagreement — not every form states every value, and marking that as a
        finding would train inspectors to ignore red.
      </p>
    </div>
  );
}
