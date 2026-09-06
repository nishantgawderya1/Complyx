import { DERIVATION } from '@/lib/fixtures';
import { ClauseRef, Mono } from '@/components/primitives/Text';
import { UnverifiedMark } from '@/components/primitives/Tags';

/**
 * Derivation view — the WPQR's own two-column form, rebuilt.
 *
 * The structure already encodes the meaning, so it is kept: actual values on
 * the left, qualified range on the right. The right column then splits into
 * what Complyx **derived from the rules** and what the WPQR **as filled**
 * actually says. Where they match, quiet. Where they diverge, a red rule
 * between them and a clause reference.
 *
 * Each derived value carries its governing clause beneath it. An inspector must
 * be able to see *why* the system says P1 through P15F, not just that it does.
 *
 * The blocked row is the important one. QW-452.1(b) cannot be evaluated while
 * the three-layer checkbox is disputed, so the cell says so rather than
 * defaulting to the common answer. Never let the interface look more certain
 * than the system is.
 */
export function Derivation() {
  const anyUnverified = DERIVATION.some((r) => !r.rule_verified);

  return (
    <div className="p-6">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div className="max-w-[70ch]">
          <h2 className="font-cond text-lg font-semibold text-ink">
            Qualified range — derived against stated
          </h2>
          <p className="mt-1 font-sans text-sm text-graphite">
            Actual values are transcribed from the raw documents. The qualified
            range is not copied from anywhere: it is computed from Section IX and
            compared against the WPQR as filled.
          </p>
        </div>
        {anyUnverified && <UnverifiedMark what="Rule table" />}
      </div>

      {anyUnverified && (
        <div className="mb-4 border border-pencil bg-pencil-soft px-3 py-2">
          <p className="max-w-[74ch] font-sans text-sm text-ink">
            The QW rule rows backing this comparison have not been signed off by
            a qualified reviewer. These derivations are usable for development
            and must not back a verdict shown to an inspector until each row
            carries a name and a date.
          </p>
        </div>
      )}

      <div className="overflow-x-auto border border-rule bg-surface">
        <table className="ruled min-w-[860px]">
          <thead>
            <tr>
              <th className="w-[190px]">QW-350 variable</th>
              <th className="w-[190px]">Actual value</th>
              <th>Complyx derives</th>
              <th>WPQR states</th>
              <th className="w-[110px]">Agreement</th>
            </tr>
          </thead>
          <tbody>
            {DERIVATION.map((row) => {
              const blocked = row.derived === null;
              return (
                <tr
                  key={row.variable}
                  className={`border-l-2 ${
                    blocked
                      ? 'border-l-pencil'
                      : row.matches
                        ? 'border-l-transparent'
                        : 'border-l-redpen'
                  }`}
                >
                  <td>
                    <div className="font-sans text-sm font-medium text-ink">
                      {row.variable}
                    </div>
                    <ClauseRef code={row.clause_ref} className="mt-0.5 block" />
                  </td>

                  <td>
                    <Mono size="xs">{row.actual}</Mono>
                  </td>

                  {/* What the rules say. Shaded, because it is computed. */}
                  <td className={blocked ? 'bg-pencil-soft' : 'bg-blueprint-soft'}>
                    {blocked ? (
                      <div>
                        <div className="font-mono text-xs font-medium uppercase tracking-label text-pencil">
                          Cannot derive
                        </div>
                        <p className="mt-0.5 max-w-[34ch] font-sans text-xs text-graphite">
                          {row.blocked_reason}
                        </p>
                      </div>
                    ) : (
                      <Mono size="xs">{row.derived}</Mono>
                    )}
                  </td>

                  {/* What a person wrote. */}
                  <td>
                    <Mono size="xs" muted={!blocked && row.matches}>
                      {row.stated}
                    </Mono>
                  </td>

                  <td>
                    {blocked ? (
                      <span className="font-mono text-2xs uppercase tracking-label text-pencil">
                        Undetermined
                      </span>
                    ) : row.matches ? (
                      <span className="font-mono text-2xs uppercase tracking-label text-stamp">
                        Matches
                      </span>
                    ) : (
                      <span className="font-mono text-2xs uppercase tracking-label text-redpen">
                        Diverges
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-3 max-w-[74ch] font-sans text-xs text-graphite">
        A shaded cell was computed by Complyx from the rule tables, never copied
        from a document. An undetermined row is not a pass: the governing input
        is unresolved, and the range cannot be checked until it is.
      </p>
    </div>
  );
}
