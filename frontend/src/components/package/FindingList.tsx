import { useEffect, useRef, useState } from 'react';
import { DOC_LABEL, SEVERITY_ORDER, type Finding } from '@/lib/types';
import { ClauseRef, Mono } from '@/components/primitives/Text';
import { SeverityTag } from '@/components/primitives/Tags';
import { Button } from '@/components/primitives/Button';
import { Stamp, DismissMark } from '@/components/primitives/Stamp';
import { EmptyState } from '@/components/primitives/Panel';

/**
 * The findings list, and the keyboard surface for the whole review.
 *
 * Inspectors reviewing forty packages will not reach for a mouse, so the list
 * owns a small set of single-key bindings: j/k or arrows to move, c to confirm,
 * d to dismiss. Confirm and dismiss are the only two verdicts. There is no
 * bulk-accept — every finding requires a human decision, and the record stores
 * who made it.
 */

export function FindingList({
  findings,
  selectedId,
  onSelect,
  onConfirm,
  onDismiss,
}: {
  findings: Finding[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onConfirm: (id: string) => void;
  onDismiss: (id: string, reason: string) => void;
}) {
  const sorted = [...findings].sort(
    (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity],
  );
  const [dismissing, setDismissing] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      // Never steal keys while the dismissal reason is being typed.
      const tag = (event.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (!sorted.length) return;

      const index = sorted.findIndex((f) => f.id === selectedId);

      if (event.key === 'j' || event.key === 'ArrowDown') {
        event.preventDefault();
        onSelect(sorted[Math.min(index + 1, sorted.length - 1)]?.id ?? sorted[0].id);
      } else if (event.key === 'k' || event.key === 'ArrowUp') {
        event.preventDefault();
        onSelect(sorted[Math.max(index - 1, 0)]?.id ?? sorted[0].id);
      } else if (event.key === 'c' && selectedId) {
        event.preventDefault();
        onConfirm(selectedId);
      } else if (event.key === 'd' && selectedId) {
        event.preventDefault();
        setDismissing(selectedId);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [sorted, selectedId, onSelect, onConfirm]);

  if (!findings.length) {
    return (
      <EmptyState
        mark={<Stamp initials="—" date="" label="No findings" />}
        headline="This package reconciles"
      >
        Every field agrees across the six documents and every derived range
        matches the WPQR as filled. Nothing requires a decision.
      </EmptyState>
    );
  }

  return (
    <div ref={listRef} className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between border-b border-rule bg-paper px-3 py-1.5">
        <span className="label">
          {findings.filter((f) => f.status === 'open').length} open of {findings.length}
        </span>
        <span className="font-mono text-2xs text-graphite">
          j/k move · c confirm · d dismiss
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {sorted.map((finding) => (
          <FindingRow
            key={finding.id}
            finding={finding}
            selected={finding.id === selectedId}
            dismissing={dismissing === finding.id}
            onSelect={() => onSelect(finding.id)}
            onConfirm={() => onConfirm(finding.id)}
            onStartDismiss={() => setDismissing(finding.id)}
            onCancelDismiss={() => setDismissing(null)}
            onDismiss={(reason) => {
              onDismiss(finding.id, reason);
              setDismissing(null);
            }}
          />
        ))}
      </div>
    </div>
  );
}

function FindingRow({
  finding,
  selected,
  dismissing,
  onSelect,
  onConfirm,
  onStartDismiss,
  onCancelDismiss,
  onDismiss,
}: {
  finding: Finding;
  selected: boolean;
  dismissing: boolean;
  onSelect: () => void;
  onConfirm: () => void;
  onStartDismiss: () => void;
  onCancelDismiss: () => void;
  onDismiss: (reason: string) => void;
}) {
  const [reason, setReason] = useState('');
  const settled = finding.status !== 'open';

  return (
    <div
      className={`border-b border-rule border-l-3 ${
        selected ? 'bg-white' : 'bg-surface'
      } ${
        finding.severity === 'CRITICAL'
          ? 'border-l-redpen'
          : finding.severity === 'MAJOR'
            ? 'border-l-pencil'
            : 'border-l-rule-strong'
      } ${settled ? 'opacity-60' : ''}`}
    >
      <button
        type="button"
        onClick={onSelect}
        className="w-full px-3 py-2.5 text-left"
        aria-current={selected}
      >
        <div className="mb-1 flex items-center gap-2">
          <SeverityTag severity={finding.severity} />
          {finding.clause_ref && <ClauseRef code={finding.clause_ref} />}
        </div>

        <div className="font-sans text-sm font-medium leading-snug text-ink">
          {finding.title}
        </div>

        {/*
          Observed and expected side by side. The observed value is the one in
          red, because that is the mark on the document.
        */}
        <div className="mt-1.5 grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5">
          <span className="label">Observed</span>
          <Mono size="xs" finding>
            {finding.observed}
          </Mono>
          <span className="label">Expected</span>
          <Mono size="xs">{finding.expected}</Mono>
        </div>

        {finding.locations.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {finding.locations.map((loc) => (
              <span
                key={`${loc.document_id}-${loc.page}`}
                className="border border-rule bg-paper px-1 font-mono text-2xs text-graphite"
              >
                {DOC_LABEL[loc.doc_type]} p{loc.page}
              </span>
            ))}
          </div>
        )}
      </button>

      {selected && !settled && (
        <div className="border-t border-rule bg-paper px-3 py-2">
          {dismissing ? (
            <div className="flex flex-col gap-2">
              {/* Dismissal without a reason is not possible. */}
              <label className="label" htmlFor={`reason-${finding.id}`}>
                Reason for dismissal (required)
              </label>
              <input
                id={`reason-${finding.id}`}
                autoFocus
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="border border-rule-strong bg-surface px-2 py-1 font-sans text-sm text-ink"
                placeholder="e.g. transcription checked against original, card reissued"
              />
              <div className="flex gap-2">
                <Button
                  variant="primary"
                  disabled={reason.trim().length < 4}
                  onClick={() => onDismiss(reason.trim())}
                >
                  Dismiss finding
                </Button>
                <Button variant="quiet" onClick={onCancelDismiss}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex gap-2">
              <Button variant="primary" shortcut="c" onClick={onConfirm}>
                Confirm
              </Button>
              <Button shortcut="d" onClick={onStartDismiss}>
                Dismiss
              </Button>
            </div>
          )}
        </div>
      )}

      {settled && (
        <div className="flex items-center gap-3 border-t border-rule bg-paper px-3 py-2">
          {finding.status === 'confirmed' ? (
            <Stamp
              initials={finding.confirmed_by ?? 'QA'}
              date={finding.confirmed_at ?? ''}
            />
          ) : (
            <DismissMark
              initials={finding.confirmed_by ?? 'QA'}
              date={finding.confirmed_at ?? ''}
              reason={finding.dismiss_reason ?? ''}
            />
          )}
          {finding.dismiss_reason && (
            <span className="font-sans text-xs text-graphite">
              {finding.dismiss_reason}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
