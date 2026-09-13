import { useMemo, useState } from 'react';
import {
  CELL_STATE_LABEL,
  SLOT_LABEL,
  type CellState,
  type Evidence,
  type WpqrCell,
  type WpqrDraft,
} from '@/lib/types';
import { ClauseRef, Mono, NotRead } from '@/components/primitives/Text';
import { Button } from '@/components/primitives/Button';
import { UnverifiedMark } from '@/components/primitives/Tags';

/**
 * Build — the screen where a WPQR is derived and signed off, row by row.
 *
 * This is the product. Everything before it is intake; everything after it is
 * output.
 *
 * The design answers the one question an inspector has about every value on a
 * record they did not transcribe: **where did this come from?** Each row opens
 * to show the full chain — which source document, which field on it, which page,
 * how it was read — and then the rule that turned the actual value into a
 * qualified range, stated in a sentence rather than as a clause number alone.
 *
 * A clause reference says which rule applied. It does not say what it was
 * applied to. Both are needed before a signature is defensible.
 *
 * Sign-off is per row and cannot be applied in bulk. A blocked or conflicted
 * row cannot be signed at all: the derivation is genuinely undetermined, and
 * the screen says so instead of offering the common answer.
 */

const STATE_STYLE: Record<CellState, string> = {
  derived: 'border-l-blueprint',
  confirmed: 'border-l-stamp',
  blocked: 'border-l-pencil',
  conflicted: 'border-l-redpen',
};

const STATE_TEXT: Record<CellState, string> = {
  derived: 'text-blueprint',
  confirmed: 'text-stamp',
  blocked: 'text-pencil',
  conflicted: 'text-redpen',
};

const GROUP_LABEL: Record<WpqrCell['group'], string> = {
  identification: 'Identification',
  variables: 'Welding variables (QW-350)',
  testing: 'Testing',
  certification: 'Certification',
};

export function BuildWpqr({
  draft,
  onConfirmCell,
  onManualEntry,
  onContinue,
}: {
  draft: WpqrDraft;
  onConfirmCell: (cellId: string) => void;
  onManualEntry: (cellId: string, value: string) => void;
  onContinue: () => void;
}) {
  const [openId, setOpenId] = useState<string | null>(null);

  const stats = useMemo(() => {
    const c = draft.cells;
    return {
      total: c.length,
      confirmed: c.filter((x) => x.state === 'confirmed').length,
      blocked: c.filter((x) => x.state === 'blocked' || x.state === 'conflicted').length,
      pending: c.filter((x) => x.state === 'derived').length,
    };
  }, [draft.cells]);

  const groups = ['identification', 'variables', 'testing', 'certification'] as const;
  const canProceed = stats.blocked === 0 && stats.pending === 0;

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-6">
      {/* ---- the state of the draft, before any scrolling ---- */}
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-[70ch]">
          <h2 className="font-cond text-lg font-semibold text-ink">
            Derived qualified range
          </h2>
          <p className="mt-1 font-sans text-sm text-graphite">
            Actual values are transcribed from the three sources. Every qualified
            range below was computed from the Section IX tables — none of it was
            copied from a document. Open a row to see the evidence and the rule.
          </p>
        </div>
        <div className="text-right">
          <div className="label">Code edition</div>
          <Mono size="xs">{draft.code_edition}</Mono>
          <div className="mt-1">
            <UnverifiedMark what="Rule table" />
          </div>
        </div>
      </div>

      <div className="mb-5 flex flex-wrap items-center gap-x-5 gap-y-1 border-y border-rule bg-paper px-3 py-2">
        <Mono size="xs">
          <span className="text-stamp">{stats.confirmed} confirmed</span>
        </Mono>
        <Mono size="xs">
          <span className="text-blueprint">{stats.pending} awaiting sign-off</span>
        </Mono>
        {stats.blocked > 0 && (
          <Mono size="xs">
            <span className="text-redpen">{stats.blocked} cannot be derived</span>
          </Mono>
        )}
        <span className="ml-auto font-sans text-xs text-graphite">
          Signing is per row. There is no bulk accept.
        </span>
      </div>

      {groups.map((group) => {
        const rows = draft.cells.filter((c) => c.group === group);
        if (!rows.length) return null;
        return (
          <section key={group} className="mb-6">
            <h3 className="label mb-2 border-b border-rule pb-1">
              {GROUP_LABEL[group]}
            </h3>
            <div className="border border-rule">
              {rows.map((cell, i) => (
                <CellRow
                  key={cell.id}
                  cell={cell}
                  last={i === rows.length - 1}
                  open={openId === cell.id}
                  onToggle={() => setOpenId(openId === cell.id ? null : cell.id)}
                  onConfirm={() => onConfirmCell(cell.id)}
                  onManualEntry={(v) => onManualEntry(cell.id, v)}
                />
              ))}
            </div>
          </section>
        );
      })}

      <div className="flex flex-wrap items-center justify-between gap-4 border-t border-rule-strong pt-4">
        <span className="max-w-[60ch] font-sans text-sm text-graphite">
          {canProceed
            ? 'Every row is signed. The draft can be issued.'
            : stats.blocked > 0
              ? 'Rows that cannot be derived must be resolved or filled in by hand before the draft can be issued.'
              : 'Every row needs a signature before the draft can be issued.'}
        </span>
        <Button variant="primary" disabled={!canProceed} onClick={onContinue}>
          Review the WPQR
        </Button>
      </div>
    </div>
  );
}

function CellRow({
  cell,
  last,
  open,
  onToggle,
  onConfirm,
  onManualEntry,
}: {
  cell: WpqrCell;
  last: boolean;
  open: boolean;
  onToggle: () => void;
  onConfirm: () => void;
  onManualEntry: (value: string) => void;
}) {
  const [manual, setManual] = useState('');
  const settled = cell.state === 'confirmed';
  const stuck = cell.state === 'blocked' || cell.state === 'conflicted';

  return (
    <div className={`border-l-3 ${STATE_STYLE[cell.state]} ${last ? '' : 'border-b border-b-rule'}`}>
      {/*
        The sign action is a sibling of the expand toggle, not inside it, so a
        row can be signed from the collapsed state in one click. Requiring an
        expand first doubled the cost of a clean package to 36 clicks, which is
        friction with no safety value -- the evidence is still one click away
        for any row the inspector actually wants to interrogate. This is not a
        bulk accept: each row is still its own deliberate decision.
      */}
      <div className="flex items-stretch">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="grid min-w-0 flex-1 grid-cols-[minmax(150px,1.1fr)_minmax(120px,1fr)_minmax(180px,1.6fr)_136px] items-start gap-3 px-3 py-2.5 text-left hover:bg-white"
      >
        <span>
          <span className="block font-sans text-sm font-medium text-ink">
            {cell.variable}
          </span>
          {cell.clause_ref && <ClauseRef code={cell.clause_ref} className="mt-0.5 block" />}
        </span>

        <span>
          {cell.actual ? <Mono size="xs">{cell.actual}</Mono> : <NotRead />}
        </span>

        {/* Derived cells are shaded: computed here, never copied. */}
        <span className={cell.derived ? 'bg-blueprint-soft px-1.5 py-0.5' : ''}>
          {cell.derived ? (
            <Mono size="xs">{cell.derived}</Mono>
          ) : stuck ? (
            <span className={`font-mono text-2xs uppercase tracking-label ${STATE_TEXT[cell.state]}`}>
              {CELL_STATE_LABEL[cell.state]}
            </span>
          ) : (
            <span className="font-mono text-2xs text-graphite">transcribed only</span>
          )}
        </span>

        <span className="text-right">
          <span
            className={`whitespace-nowrap font-mono text-2xs uppercase tracking-label ${STATE_TEXT[cell.state]}`}
          >
            {settled ? `✓ ${cell.confirmed_by}` : CELL_STATE_LABEL[cell.state]}
          </span>
          <span className="mt-0.5 block font-mono text-2xs text-graphite">
            {open ? 'hide' : 'evidence'}
          </span>
        </span>
      </button>

        {!settled && !stuck && (
          <button
            type="button"
            onClick={onConfirm}
            title={`Sign off ${cell.variable}`}
            className="shrink-0 border-l border-rule px-4 font-mono text-2xs font-medium uppercase tracking-label text-blueprint hover:bg-blueprint-soft"
          >
            Sign
          </button>
        )}
      </div>

      {open && (
        <div className="border-t border-rule bg-paper px-3 py-3">
          {/* ---- where the actual value came from ---- */}
          <div className="label mb-1.5">Evidence</div>
          {cell.evidence.length ? (
            <ol className="mb-3 flex flex-col gap-1.5">
              {cell.evidence.map((e, i) => (
                <EvidenceLine key={`${e.slot}-${i}`} evidence={e} />
              ))}
            </ol>
          ) : (
            <p className="mb-3 font-sans text-sm text-graphite">
              No source field — this row is entered by hand or derived from other rows.
            </p>
          )}

          {/* ---- the rule that produced the range ---- */}
          {cell.rule_note && (
            <>
              <div className="label mb-1">Rule applied</div>
              <p className="mb-3 max-w-[78ch] border-l-2 border-blueprint bg-blueprint-soft px-3 py-2 font-sans text-sm text-ink">
                {cell.rule_note}
                {cell.clause_ref && (
                  <span className="mt-1 block">
                    <ClauseRef code={cell.clause_ref} />
                  </span>
                )}
              </p>
            </>
          )}

          {cell.blocked_reason && (
            <>
              <div className="label mb-1">Why this cannot be derived</div>
              <p
                className={`mb-3 max-w-[78ch] border-l-2 px-3 py-2 font-sans text-sm text-ink ${
                  cell.state === 'conflicted'
                    ? 'border-redpen bg-redpen-soft'
                    : 'border-pencil bg-pencil-soft'
                }`}
              >
                {cell.blocked_reason}
              </p>
            </>
          )}

          <div className="flex flex-wrap items-center gap-3">
            {settled ? (
              <span className="font-mono text-2xs uppercase tracking-label text-stamp">
                {cell.manual_entry ? 'Entered by hand and signed by ' : 'Signed by '}
                {cell.confirmed_by} on {cell.confirmed_at}
              </span>
            ) : stuck ? (
              <div className="flex w-full flex-col gap-2">
                <label className="label" htmlFor={`manual-${cell.id}`}>
                  Enter this value by hand
                </label>
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    id={`manual-${cell.id}`}
                    value={manual}
                    onChange={(e) => setManual(e.target.value)}
                    placeholder={
                      cell.state === 'conflicted'
                        ? 'Read it off the document'
                        : 'State the range, with the clause you are relying on'
                    }
                    className="min-w-[320px] flex-1 border border-rule-strong bg-surface px-2 py-1 font-mono text-sm text-ink"
                  />
                  <Button
                    variant="primary"
                    disabled={manual.trim().length < 2}
                    onClick={() => onManualEntry(manual.trim())}
                  >
                    Record and sign
                  </Button>
                </div>
                <span className="max-w-[74ch] font-sans text-xs text-graphite">
                  Complyx did not derive this. A hand-entered value is marked as
                  such on the issued record, so a reader can tell which cells the
                  system stands behind and which you supplied.
                </span>
              </div>
            ) : (
              <>
                <Button variant="primary" onClick={onConfirm}>
                  Sign off this row
                </Button>
                {!cell.rule_verified && (
                  <span className="font-sans text-xs text-pencil">
                    The governing rule row is not reviewer-signed. Signing here
                    accepts an unverified rule.
                  </span>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** One link in the chain: document, field, page, and how it was read. */
function EvidenceLine({ evidence }: { evidence: Evidence }) {
  const degraded =
    evidence.read_method !== 'template_region' &&
    evidence.read_method !== 'checkbox_agreed';
  return (
    <li className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 border-l-2 border-rule-strong pl-2.5">
      <span className="font-sans text-xs font-medium text-ink">
        {SLOT_LABEL[evidence.slot]}
      </span>
      <span className="font-mono text-2xs text-graphite">
        p{evidence.page} · {evidence.field_label}
      </span>
      <Mono size="xs">{evidence.value}</Mono>
      <span
        className={`font-mono text-2xs ${degraded ? 'text-pencil' : 'text-graphite'}`}
        title={evidence.read_method}
      >
        {degraded ? 'fallback region' : 'anchored'} {evidence.confidence.toFixed(2)}
      </span>
    </li>
  );
}
