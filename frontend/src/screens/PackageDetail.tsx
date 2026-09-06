import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { WORKLIST } from '@/lib/fixtures';
import type { Finding } from '@/lib/types';
import { ScreenHead } from '@/components/primitives/Panel';
import { ClearMark, StatusTag } from '@/components/primitives/Tags';
import { Mono, Field } from '@/components/primitives/Text';
import { CompletenessLine } from '@/components/primitives/DocSquares';
import { FolderTabs } from '@/components/package/FolderTabs';
import { FindingList } from '@/components/package/FindingList';
import {
  DocumentCanvas,
  LayerToggles,
} from '@/components/document/DocumentCanvas';
import { Reconciliation } from './Reconciliation';
import { Derivation } from './Derivation';

/**
 * Package detail — the central working screen.
 *
 * Findings on the left, document canvas on the right, bound both ways:
 * selecting a finding scrolls the canvas to the exact page and highlights the
 * exact region; selecting a mark on the canvas selects its finding. That
 * two-way binding is the point of the whole screen.
 *
 * The header answers the two questions an inspector has before scrolling:
 * *which package*, and *is it clean*.
 */

type View = 'audit' | 'reconciliation' | 'derivation';

export function PackageDetail() {
  const { id } = useParams<{ id: string }>();
  const pkg = WORKLIST.find((p) => p.id === id) ?? WORKLIST[0];

  const [findings, setFindings] = useState<Finding[]>(pkg.findings);
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(
    pkg.findings[0]?.id ?? null,
  );
  const [view, setView] = useState<View>('audit');
  const [showExtraction, setShowExtraction] = useState(false);
  const [showMarkup, setShowMarkup] = useState(true);

  /**
   * Selecting a finding follows it to the document it was found on, so the
   * canvas never shows a page the selected mark is not on.
   */
  const selectedFinding = findings.find((f) => f.id === selectedFindingId) ?? null;
  const [manualDocId, setManualDocId] = useState<string | null>(null);

  const activeDocId =
    manualDocId ??
    selectedFinding?.locations[0]?.document_id ??
    pkg.documents[0]?.id ??
    null;

  const activeDoc =
    pkg.documents.find((d) => d.id === activeDocId) ?? pkg.documents[0];

  const activePage =
    selectedFinding?.locations.find((l) => l.document_id === activeDoc?.id)?.page ?? 1;

  const counts = useMemo(
    () => ({
      critical: findings.filter((f) => f.severity === 'CRITICAL').length,
      major: findings.filter((f) => f.severity === 'MAJOR').length,
      open: findings.filter((f) => f.status === 'open').length,
    }),
    [findings],
  );

  const today = new Date().toISOString().slice(0, 10);

  function confirm(findingId: string) {
    setFindings((prev) =>
      prev.map((f) =>
        f.id === findingId
          ? { ...f, status: 'confirmed', confirmed_by: 'RK', confirmed_at: today }
          : f,
      ),
    );
  }

  function dismiss(findingId: string, reason: string) {
    setFindings((prev) =>
      prev.map((f) =>
        f.id === findingId
          ? {
              ...f,
              status: 'dismissed',
              confirmed_by: 'RK',
              confirmed_at: today,
              dismiss_reason: reason,
            }
          : f,
      ),
    );
  }

  const markCount = activeDoc
    ? findings.reduce(
        (n, f) =>
          n + f.locations.filter((l) => l.document_id === activeDoc.id).length,
        0,
      )
    : 0;

  return (
    <>
      <ScreenHead
        eyebrow={`${pkg.project} · ${pkg.client}`}
        title={
          <span className="flex items-baseline gap-3">
            <span className="font-mono">{pkg.coupon_no}</span>
            <span className="font-sans text-base font-normal text-graphite">
              {pkg.welder_name}
            </span>
            <Mono size="sm" muted>
              {pkg.welder_id}
            </Mono>
          </span>
        }
        right={<StatusTag status={pkg.status} />}
      >
        {/* "Is it clean" — answered in one line, before any scrolling. */}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          {counts.critical + counts.major === 0 ? (
            <ClearMark>Package reconciles</ClearMark>
          ) : (
            <span className="font-sans text-sm text-ink">
              <span className="font-medium text-redpen">{counts.critical} critical</span>
              {counts.major > 0 && (
                <span className="text-pencil"> · {counts.major} major</span>
              )}
              <span className="text-graphite"> · {counts.open} awaiting decision</span>
            </span>
          )}
          <CompletenessLine present={pkg.documents.map((d) => d.doc_type)} />
        </div>

        <div className="mt-3 grid max-w-3xl grid-cols-4 gap-4">
          <Field label="WPS">{pkg.wps_no}</Field>
          <Field label="Test date">{pkg.test_date ?? '—'}</Field>
          <Field label="Received">{pkg.received_date}</Field>
          <Field label="Contractor">{pkg.contractor}</Field>
        </div>
      </ScreenHead>

      {/* ---- view switch ---- */}
      <div className="no-print flex gap-px border-b border-rule bg-paper px-4">
        {(
          [
            ['audit', 'Audit'],
            ['reconciliation', 'Reconciliation grid'],
            ['derivation', 'Derivation'],
          ] as [View, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setView(key)}
            className={`border-b-2 px-3 py-2 font-sans text-sm transition-colors duration-120 ${
              view === key
                ? 'border-blueprint font-medium text-blueprint'
                : 'border-transparent text-graphite hover:text-ink'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {view === 'reconciliation' && (
        <div className="min-h-0 flex-1 overflow-auto">
          <Reconciliation
            onOpenFinding={(fid) => {
              setSelectedFindingId(fid);
              setManualDocId(null);
              setView('audit');
            }}
          />
        </div>
      )}

      {view === 'derivation' && (
        <div className="min-h-0 flex-1 overflow-auto">
          <Derivation />
        </div>
      )}

      {view === 'audit' && (
        <div className="flex min-h-0 flex-1 overflow-hidden">
          {/* ---- findings ---- */}
          <div className="flex w-[380px] shrink-0 flex-col border-r border-rule bg-surface">
            <FindingList
              findings={findings}
              selectedId={selectedFindingId}
              onSelect={(fid) => {
                setSelectedFindingId(fid);
                setManualDocId(null);
              }}
              onConfirm={confirm}
              onDismiss={dismiss}
            />
          </div>

          {/* ---- document ---- */}
          <div className="flex min-w-0 flex-1 flex-col">
            <FolderTabs
              documents={pkg.documents}
              selectedId={activeDoc?.id ?? null}
              onSelect={setManualDocId}
            />
            <div className="flex items-center justify-between border-b border-rule bg-surface px-4 py-1.5">
              <span className="titleblock">
                {activeDoc?.format_no} {activeDoc?.format_rev}
              </span>
              <LayerToggles
                showExtraction={showExtraction}
                showMarkup={showMarkup}
                onToggleExtraction={() => setShowExtraction((v) => !v)}
                onToggleMarkup={() => setShowMarkup((v) => !v)}
                markCount={markCount}
              />
            </div>
            {activeDoc && (
              <div className="min-h-0 flex-1">
                <DocumentCanvas
                  document={activeDoc}
                  page={activePage}
                  findings={findings}
                  selectedFindingId={selectedFindingId}
                  onSelectFinding={setSelectedFindingId}
                  showExtraction={showExtraction}
                  showMarkup={showMarkup}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
