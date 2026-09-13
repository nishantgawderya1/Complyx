import { useState } from 'react';
import type { WpqrDraft } from '@/lib/types';
import { ClauseRef, Mono } from '@/components/primitives/Text';
import { Button, SignOffButton } from '@/components/primitives/Button';
import { Stamp } from '@/components/primitives/Stamp';

/**
 * The issued record.
 *
 * Laid out as FQ/069 Rev.2 — the site's implementation of QW-484A. Section IX
 * calls QW-484A a *suggested* format, so the governing layout is the one NPCIL
 * actually signs, not the one in the appendix.
 *
 * Until it is signed the page carries a DRAFT overlay that prints. That is
 * deliberate and it is the single most important thing on this screen: a
 * generated qualification record that leaves the building looking final, before
 * a qualified person has attested to it, is the failure this whole product is
 * built to avoid. The watermark is in the print stylesheet, not just on screen.
 */
export function WpqrOutput({
  draft,
  onSign,
}: {
  draft: WpqrDraft;
  onSign: (initials: string) => void;
}) {
  const [initials, setInitials] = useState('');
  const signed = Boolean(draft.signed_by);

  const identification = draft.cells.filter((c) => c.group === 'identification');
  const variables = draft.cells.filter((c) => c.group === 'variables');
  const testing = draft.cells.filter(
    (c) => c.group === 'testing' || c.group === 'certification',
  );

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-6">
      {/* ---- actions, not printed ---- */}
      <div className="no-print mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-cond text-lg font-semibold text-ink">
            {signed ? 'Issued record' : 'Draft record'}
          </h2>
          <p className="mt-0.5 font-sans text-sm text-graphite">
            {signed
              ? 'Signed and ready to file. The watermark is removed on print.'
              : 'Not a qualification record until signed. Prints watermarked.'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => window.print()}>Print</Button>
        </div>
      </div>

      {/* ---- the form ---- */}
      <div className="relative border border-ink bg-surface">
        {!signed && (
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center overflow-hidden"
          >
            {/*
              Stacked rather than one long line: a single 86px string of
              "Draft - not a qualification record" is wider than the form and
              clips to an unreadable fragment. An illegible warning is the same
              as no warning.
            */}
            <span
              className="flex flex-col items-center text-redpen opacity-[0.11]"
              style={{ transform: 'rotate(-22deg)' }}
            >
              <span className="font-cond text-[110px] font-bold uppercase leading-none tracking-[0.2em]">
                Draft
              </span>
              <span className="mt-2 whitespace-nowrap font-cond text-[21px] font-semibold uppercase tracking-[0.3em]">
                Not a qualification record
              </span>
            </span>
          </div>
        )}

        {/* form header */}
        <div className="border-b-2 border-ink px-4 py-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="font-cond text-base font-semibold uppercase tracking-label text-ink">
                Welder Performance Qualification Record
              </div>
              <div className="mt-0.5 font-mono text-2xs text-graphite">
                (WPQR) · Reference: QW-301 of Section IX, ASME BPV Code
              </div>
            </div>
            <div className="text-right">
              <div className="titleblock">
                Form No. {draft.form_no} {draft.form_rev}
              </div>
              <div className="titleblock mt-0.5">{draft.code_edition}</div>
            </div>
          </div>
        </div>

        {/* identification block */}
        <table className="w-full border-collapse">
          <tbody>
            {identification.map((cell) => (
              <tr key={cell.id} className="border-b border-rule">
                <th
                  scope="row"
                  className="w-[42%] border-r border-rule px-3 py-1.5 text-left align-top font-sans text-sm font-normal text-graphite"
                >
                  {cell.variable}
                </th>
                <td className="px-3 py-1.5 align-top">
                  {cell.actual ? (
                    <Mono size="sm">{cell.actual}</Mono>
                  ) : (
                    <span className="font-mono text-xs text-pencil">
                      — to be entered
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* the two-column heart of the form */}
        <div className="border-t-2 border-ink">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-ink bg-paper">
                <th className="w-[30%] border-r border-rule px-3 py-1.5 text-left align-bottom">
                  <span className="label">Welding variable (QW-350)</span>
                </th>
                <th className="w-[24%] border-r border-rule px-3 py-1.5 text-left align-bottom">
                  <span className="label">Actual value</span>
                </th>
                <th className="px-3 py-1.5 text-left align-bottom">
                  <span className="label">Range qualified</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {variables.map((cell) => (
                <tr key={cell.id} className="border-b border-rule">
                  <th
                    scope="row"
                    className="border-r border-rule px-3 py-2 text-left align-top font-sans text-sm font-normal text-ink"
                  >
                    {cell.variable}
                    {cell.clause_ref && (
                      <ClauseRef code={cell.clause_ref} className="mt-0.5 block" />
                    )}
                  </th>
                  <td className="border-r border-rule px-3 py-2 align-top">
                    <Mono size="xs">{cell.actual ?? '—'}</Mono>
                  </td>
                  <td className="px-3 py-2 align-top">
                    {cell.derived ? (
                      <Mono size="xs">{cell.derived}</Mono>
                    ) : (
                      <span className="font-mono text-2xs uppercase tracking-label text-pencil">
                        Not derived — see draft notes
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* testing and certification */}
        <div className="border-t-2 border-ink">
          <table className="w-full border-collapse">
            <tbody>
              {testing.map((cell) => (
                <tr key={cell.id} className="border-b border-rule">
                  <th
                    scope="row"
                    className="w-[42%] border-r border-rule px-3 py-1.5 text-left align-top font-sans text-sm font-normal text-graphite"
                  >
                    {cell.variable}
                    {cell.clause_ref && (
                      <ClauseRef code={cell.clause_ref} className="ml-2" />
                    )}
                  </th>
                  <td className="px-3 py-1.5 align-top">
                    {cell.actual ? (
                      <Mono size="sm">{cell.actual}</Mono>
                    ) : (
                      <span className="font-mono text-xs text-pencil">
                        — to be entered
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* certification block */}
        <div className="border-t-2 border-ink px-4 py-3">
          <p className="max-w-[86ch] font-sans text-xs text-ink">
            We certify that the statements in this record are correct and that the
            test coupons were prepared, welded and tested in accordance with the
            requirements of Section IX of the ASME Boiler and Pressure Vessel Code.
          </p>

          <div className="mt-3 grid grid-cols-3 gap-6">
            <SignatureBlock role="Prepared by (TPL)" filled={signed ? draft.signed_by : undefined} date={draft.signed_at} />
            <SignatureBlock role="Reviewed by (TPL QA)" />
            <SignatureBlock role="Certified by (NPCIL)" />
          </div>

          {/* provenance — an auditor's first question */}
          <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 border-t border-rule pt-2">
            <span className="titleblock">Rule tables: {draft.kb_version}</span>
            <span className="titleblock">Code: {draft.code_edition}</span>
            <span className="titleblock">
              Sources: {draft.sources.map((s) => s.canonical_key).join(' · ')}
            </span>
          </div>
        </div>
      </div>

      {/* ---- sign-off, not printed ---- */}
      {!signed && (
        <div className="no-print mt-5 border-2 border-stamp bg-surface px-4 py-4">
          <div className="label mb-1">Attestation</div>
          <p className="mb-3 max-w-[74ch] font-sans text-sm text-ink">
            Signing issues this as a welder performance qualification record. You
            are attesting that the actual values match the source documents and
            that the qualified ranges are correct for this coupon under{' '}
            {draft.code_edition}. Your name and the time are recorded against every
            row.
          </p>
          <div className="mb-3 border-l-2 border-pencil bg-pencil-soft px-3 py-2">
            <p className="max-w-[74ch] font-sans text-sm text-ink">
              The rule tables backing these ranges are{' '}
              <strong>not reviewer-signed</strong> ({draft.kb_version}). Until a
              qualified reviewer signs each QW row, this draft is for development
              and review only and must not be issued to the field.
            </p>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1">
              <span className="label">Your initials</span>
              <input
                value={initials}
                onChange={(e) => setInitials(e.target.value.toUpperCase().slice(0, 4))}
                className="w-24 border border-rule-strong bg-surface px-2 py-1 font-mono text-sm uppercase text-ink"
                placeholder="RK"
              />
            </label>
            <SignOffButton
              disabled={initials.trim().length < 2}
              onClick={() => onSign(initials.trim())}
            >
              Sign and issue
            </SignOffButton>
          </div>
        </div>
      )}

      {signed && (
        <div className="no-print mt-5 flex items-center gap-4 border border-stamp bg-stamp-soft px-4 py-3">
          <Stamp initials={draft.signed_by!} date={draft.signed_at!} label="Issued" />
          <span className="font-sans text-sm text-ink">
            Issued by {draft.signed_by} on {draft.signed_at}. Every row carries its
            own signature and the evidence it was derived from.
          </span>
        </div>
      )}
    </div>
  );
}

function SignatureBlock({
  role,
  filled,
  date,
}: {
  role: string;
  filled?: string;
  date?: string;
}) {
  return (
    <div>
      <div className="flex h-10 items-end border-b border-ink">
        {filled && (
          <span className="pb-1 font-mono text-sm text-stamp">{filled}</span>
        )}
      </div>
      <div className="label mt-1">{role}</div>
      <div className="font-mono text-2xs text-graphite">{date ?? 'Date:'}</div>
    </div>
  );
}
