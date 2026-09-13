import { useState } from 'react';
import {
  SLOT_LABEL,
  SOURCE_SLOTS,
  type SourceSlot,
  type UploadedFile,
  type WpqrDraft,
} from '@/lib/types';
import { DRAFT, SOURCE_AGREEMENT } from '@/lib/wpqr-fixtures';
import { Mono } from '@/components/primitives/Text';
import { Button } from '@/components/primitives/Button';
import { Intake } from './Intake';
import { BuildWpqr } from './BuildWpqr';
import { WpqrOutput } from './WpqrOutput';

/**
 * The WPQR flow: three documents in, one signed record out.
 *
 * Four steps, linear, because the work is linear — you cannot reconcile before
 * you have the documents, derive before the sources agree, or sign before the
 * rows are derived. The step bar is a route card: it shows the whole job and
 * where it has got to, the way a traveller sheet follows a part through a shop.
 *
 * NOTE: the backend has no upload or audit endpoint yet (`api/routes/` is
 * empty), so classification and extraction here are simulated from the
 * filename and the screens read fixture data. The banner says so on every step
 * rather than in a code comment, because a demo that looks live and is not is
 * the same class of lie this product exists to prevent.
 */

type Step = 0 | 1 | 2 | 3;

const STEPS = [
  { n: 1, label: 'Sources', hint: 'Upload three documents' },
  { n: 2, label: 'Agreement', hint: 'Do the sources agree?' },
  { n: 3, label: 'Derive', hint: 'Apply Section IX, sign each row' },
  { n: 4, label: 'Record', hint: 'Issue the WPQR' },
] as const;

/** Filename patterns for the demo's simulated classifier. */
const SIMULATED: { match: RegExp; slot: SourceSlot; key: string; raw: string }[] = [
  {
    match: /requisition/i,
    slot: 'requisition',
    key: 'TF-216',
    raw: 'Format No: NPCIL/QMD/TF/216',
  },
  {
    match: /data.?record|wdr/i,
    slot: 'weld_data_record',
    key: 'TF-114-R0',
    raw: 'Format No: NPCIL/OMD/TE. 114(R0)',
  },
  {
    match: /lab|test.?report|star.?wire/i,
    slot: 'lab_report',
    key: 'SWILPL-078F-01',
    raw: 'SWILPL/7.8F/01',
  },
];

export function WpqrFlow() {
  const [step, setStep] = useState<Step>(0);
  /**
   * The furthest step reached, which is what gates navigation -- not the
   * current step. Gating on `step` alone makes the route card a one-way trap:
   * an inspector who clicks back to re-check a source document finds the later
   * steps disabled and has to re-walk the whole flow to return to the row they
   * were signing. Going back to look at something is the most ordinary thing
   * they do.
   */
  const [furthest, setFurthest] = useState<Step>(0);

  function goto(next: Step) {
    setStep(next);
    setFurthest((f) => (next > f ? next : f));
  }
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [draft, setDraft] = useState<WpqrDraft>(DRAFT);

  function addFiles(incoming: File[]) {
    const next: UploadedFile[] = incoming.map((file) => {
      const hit = SIMULATED.find((s) => s.match.test(file.name));
      if (!hit) {
        return {
          slot: null,
          filename: file.name,
          size_bytes: file.size,
          state: 'template_unknown',
          reason:
            'No known format number was found on this document. It has not been placed — assign it by hand, or check it is one of the three sources.',
        };
      }
      return {
        slot: hit.slot,
        filename: file.name,
        size_bytes: file.size,
        state: 'matched',
        canonical_key: hit.key,
        raw_format_text: hit.raw,
        confidence: 0.93,
        page_count: 1,
      };
    });

    setFiles((prev) => {
      const merged = [...prev];
      next.forEach((f) => {
        // A slot holds one document. Re-uploading replaces rather than stacks.
        const existing = merged.findIndex((m) => m.slot && m.slot === f.slot);
        if (f.slot && existing >= 0) merged[existing] = f;
        else merged.push(f);
      });
      return merged;
    });
  }

  function assign(filename: string, slot: SourceSlot) {
    setFiles((prev) =>
      prev.map((f) => (f.filename === filename ? { ...f, slot, state: 'matched' } : f)),
    );
  }

  function remove(filename: string) {
    setFiles((prev) => prev.filter((f) => f.filename !== filename));
  }

  function confirmCell(cellId: string) {
    const today = new Date().toISOString().slice(0, 10);
    setDraft((d) => ({
      ...d,
      cells: d.cells.map((c) =>
        c.id === cellId
          ? { ...c, state: 'confirmed', confirmed_by: 'RK', confirmed_at: today }
          : c,
      ),
    }));
  }

  function manualEntry(cellId: string, value: string) {
    const today = new Date().toISOString().slice(0, 10);
    setDraft((d) => ({
      ...d,
      cells: d.cells.map((c) =>
        c.id === cellId
          ? {
              ...c,
              // The value goes into whichever column the row was missing.
              actual: c.actual ?? value,
              derived: c.actual ? value : c.derived,
              state: 'confirmed',
              manual_entry: true,
              confirmed_by: 'RK',
              confirmed_at: today,
            }
          : c,
      ),
    }));
  }

  function sign(initials: string) {
    setDraft((d) => ({
      ...d,
      signed_by: initials,
      signed_at: new Date().toISOString().slice(0, 10),
    }));
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="no-print border-b border-rule-strong bg-surface px-6 pt-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="label mb-1">
              GHAVP-1&amp;2 Main Plant · NPCIL · Tata Projects Ltd.
            </div>
            <h1 className="font-cond text-xl font-semibold leading-none text-ink">
              Build a WPQR
              {draft.coupon_no && step > 0 && (
                <span className="ml-3 font-mono text-base font-normal text-graphite">
                  {draft.coupon_no}
                </span>
              )}
            </h1>
          </div>
          <div className="text-right">
            <div className="label">Form</div>
            <Mono size="xs">
              {draft.form_no} {draft.form_rev}
            </Mono>
          </div>
        </div>

        {/* route card */}
        <nav className="mt-3 flex gap-px" aria-label="Progress">
          {STEPS.map((s, i) => {
            const state = i === step ? 'here' : i < step ? 'done' : 'todo';
            return (
              <button
                key={s.n}
                type="button"
                disabled={i > furthest}
                onClick={() => goto(i as Step)}
                className={`flex-1 border-b-2 px-3 py-2 text-left transition-colors duration-120 disabled:cursor-not-allowed ${
                  state === 'here'
                    ? 'border-blueprint bg-blueprint-soft'
                    : state === 'done'
                      ? 'border-stamp bg-surface hover:bg-paper'
                      : 'border-rule bg-surface opacity-50'
                }`}
              >
                <span className="flex items-baseline gap-2">
                  <span
                    className={`font-mono text-2xs ${
                      state === 'done' ? 'text-stamp' : 'text-graphite'
                    }`}
                  >
                    {state === 'done' ? '✓' : s.n}
                  </span>
                  <span
                    className={`font-cond text-base font-semibold ${
                      state === 'here' ? 'text-blueprint' : 'text-ink'
                    }`}
                  >
                    {s.label}
                  </span>
                </span>
                <span className="mt-0.5 block font-sans text-xs text-graphite">
                  {s.hint}
                </span>
              </button>
            );
          })}
        </nav>
      </header>

      {/* Honest about what is and is not connected. */}
      <div className="no-print border-b border-pencil bg-pencil-soft px-6 py-1.5">
        <span className="font-sans text-xs text-ink">
          <strong>Demo data.</strong> The backend has no upload or audit endpoint
          yet, so classification is simulated from the filename and the derived
          values below are fixtures, not read from your files.
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        {step === 0 && (
          <Intake
            files={files}
            onFiles={addFiles}
            onAssign={assign}
            onRemove={remove}
            onContinue={() => goto(1)}
          />
        )}
        {step === 1 && <Agreement onContinue={() => goto(2)} onBack={() => goto(0)} />}
        {step === 2 && (
          <BuildWpqr
            draft={draft}
            onConfirmCell={confirmCell}
            onManualEntry={manualEntry}
            onContinue={() => goto(3)}
          />
        )}
        {step === 3 && <WpqrOutput draft={draft} onSign={sign} />}
      </div>
    </div>
  );
}

/**
 * Step 2 — do the three sources agree?
 *
 * A precondition, not a nicety. Every derived range rests on an actual value,
 * and an actual value that two documents state differently is not a fact yet.
 * Agreement reads as a clean row, so a disagreement is visible before it is
 * read.
 */
function Agreement({ onContinue, onBack }: { onContinue: () => void; onBack: () => void }) {
  const conflicts = SOURCE_AGREEMENT.filter((r) => !r.agrees).length;
  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-6">
      <div className="mb-4 max-w-[74ch]">
        <h2 className="font-cond text-lg font-semibold text-ink">
          Agreement across the three sources
        </h2>
        <p className="mt-1 font-sans text-sm text-graphite">
          Each row is one field as every source states it. A derived range is only
          as good as the actual value under it, so disagreement here is settled
          before anything is derived.
        </p>
      </div>

      <div className="overflow-x-auto border border-rule bg-surface">
        <table className="ruled min-w-[760px]">
          <thead>
            <tr>
              <th className="w-[22%]">Field</th>
              {SOURCE_SLOTS.map((s) => (
                <th key={s}>{SLOT_LABEL[s]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {SOURCE_AGREEMENT.map((row) => (
              <tr
                key={row.field}
                className={`border-l-2 ${row.agrees ? 'border-l-transparent' : 'border-l-redpen'}`}
              >
                <th
                  scope="row"
                  className="border-b border-rule px-3 py-2 text-left align-top font-sans text-sm font-medium text-ink"
                >
                  {row.field}
                </th>
                {SOURCE_SLOTS.map((slot) => {
                  const value = row.values[slot];
                  return (
                    <td key={slot}>
                      {value == null ? (
                        <span className="font-mono text-xs text-rule-strong">·</span>
                      ) : (
                        <Mono size="xs" muted={row.agrees}>
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

      <p className="mt-3 max-w-[74ch] font-sans text-xs text-graphite">
        A dot means the document does not carry that field. Absence is not
        disagreement — not every form states every value.
      </p>

      <div className="mt-5 flex items-center justify-between gap-4 border-t border-rule-strong pt-4">
        <Button variant="quiet" onClick={onBack}>
          Back to sources
        </Button>
        <div className="flex items-center gap-3">
          <span className="font-sans text-sm text-graphite">
            {conflicts === 0
              ? 'All stated fields agree.'
              : `${conflicts} field${conflicts > 1 ? 's' : ''} disagree and must be settled first.`}
          </span>
          <Button variant="primary" disabled={conflicts > 0} onClick={onContinue}>
            Derive qualified range
          </Button>
        </div>
      </div>
    </div>
  );
}
