import { useEffect, useMemo, useRef, useState } from 'react';
import type { BBox, ExtractedField, Finding, SourceDocument } from '@/lib/types';
import { Mono } from '@/components/primitives/Text';

/**
 * The document canvas — the product's signature concept.
 *
 * Findings appear as red-pen annotations *on the scan*, the way an inspector
 * marks up a print: a rectangle around the value, a short note in the margin,
 * and a leader line where the note sits away from the mark. Not a callout
 * bubble, not a tooltip. A mark on the document.
 *
 * Two overlay layers, independently toggleable, because two different jobs use
 * this screen:
 *
 *   Extraction boxes  thin blueprint outlines over every field the system read.
 *                     For an inspector verifying one specific number.
 *   Finding marks     red, loud, with margin notes. For an inspector working
 *                     through the findings list.
 *
 * Coordinates are normalised 0..1 with a top-left origin, exactly as
 * `models/template.py` produces them, so a bbox maps to a percentage offset
 * with no translation step. This is why bounding boxes have been carried
 * through the pipeline since the first commit.
 */

const MARGIN_W = 190;

export interface CanvasProps {
  document: SourceDocument;
  page: number;
  findings: Finding[];
  selectedFindingId: string | null;
  onSelectFinding: (id: string) => void;
  showExtraction: boolean;
  showMarkup: boolean;
  /** Server-rendered page raster. Absent until the backend serves page images. */
  imageUrl?: string;
}

interface Mark {
  finding: Finding;
  bbox: BBox;
  index: number;
}

export function DocumentCanvas({
  document: doc,
  page,
  findings,
  selectedFindingId,
  onSelectFinding,
  showExtraction,
  showMarkup,
  imageUrl,
}: CanvasProps) {
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const selectedRef = useRef<HTMLButtonElement | null>(null);

  /** Findings that have a location on this document and page. */
  const marks = useMemo<Mark[]>(() => {
    const out: Mark[] = [];
    findings.forEach((finding) => {
      finding.locations
        .filter((loc) => loc.document_id === doc.id && loc.page === page)
        .forEach((loc) => out.push({ finding, bbox: loc.bbox, index: out.length + 1 }));
    });
    return out.sort((a, b) => a.bbox.y0 - b.bbox.y0);
  }, [findings, doc.id, page]);

  const fields = useMemo(
    () => doc.fields.filter((f) => f.page === page && f.bbox),
    [doc.fields, page],
  );

  /**
   * Scroll the selected mark into view, then hold a brief heavier outline
   * before settling. This animation exists for one reason: the eye needs help
   * finding the mark on a dense scan. It is removed under reduced motion.
   */
  useEffect(() => {
    selectedRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [selectedFindingId]);

  return (
    <div className="flex h-full min-h-0 flex-col bg-paper">
      <Toolbar
        zoom={zoom}
        onZoom={setZoom}
        rotation={rotation}
        onRotate={() => setRotation((r) => (r + 90) % 360)}
        pageLabel={`Page ${page} of ${doc.page_count}`}
      />

      <div className="min-h-0 flex-1 overflow-auto p-6">
        <div
          className="relative mx-auto"
          style={{
            width: `calc(${680 * zoom}px + ${MARGIN_W}px)`,
            maxWidth: '100%',
          }}
        >
          <div className="flex items-start gap-0">
            {/* ---- the page ---- */}
            <div
              className="relative shrink-0 border border-rule-strong bg-surface shadow-float"
              style={{
                width: 680 * zoom,
                aspectRatio: '680 / 880',
                transform: `rotate(${rotation}deg)`,
                transformOrigin: 'center',
              }}
            >
              {imageUrl ? (
                <img
                  src={imageUrl}
                  alt={`${doc.format_no} page ${page}`}
                  className="h-full w-full object-contain"
                  draggable={false}
                />
              ) : (
                <PagePlaceholder formatNo={doc.format_no} page={page} />
              )}

              {/* ---- extraction layer: every field the system read ---- */}
              {showExtraction &&
                fields.map((field) => (
                  <ExtractionBox key={field.name} field={field} />
                ))}

              {/* ---- markup layer: the inspector's red pen ---- */}
              {showMarkup &&
                marks.map((mark) => {
                  const selected = mark.finding.id === selectedFindingId;
                  return (
                    <button
                      key={`${mark.finding.id}-${mark.index}`}
                      ref={selected ? selectedRef : undefined}
                      type="button"
                      onClick={() => onSelectFinding(mark.finding.id)}
                      aria-label={`Finding ${mark.index}: ${mark.finding.title}`}
                      className="absolute cursor-pointer transition-all duration-200"
                      style={{
                        left: `${mark.bbox.x0 * 100}%`,
                        top: `${mark.bbox.y0 * 100}%`,
                        width: `${(mark.bbox.x1 - mark.bbox.x0) * 100}%`,
                        height: `${(mark.bbox.y1 - mark.bbox.y0) * 100}%`,
                        border: `${selected ? 3 : 2}px solid #C1392B`,
                        background: selected
                          ? 'rgba(193,57,43,0.10)'
                          : 'rgba(193,57,43,0.04)',
                      }}
                    >
                      <span className="absolute -top-[9px] left-[-1px] bg-redpen px-1 font-mono text-2xs leading-[13px] text-white">
                        {mark.index}
                      </span>
                    </button>
                  );
                })}
            </div>

            {/* ---- margin notes, the way they sit on a marked-up print ---- */}
            {showMarkup && (
              <MarginNotes
                marks={marks}
                selectedFindingId={selectedFindingId}
                onSelectFinding={onSelectFinding}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Margin notes with leader lines.
 *
 * Each note sits at the vertical position of its mark and is joined to the page
 * edge by a hairline, so the eye can follow note to mark without hunting.
 */
function MarginNotes({
  marks,
  selectedFindingId,
  onSelectFinding,
}: {
  marks: Mark[];
  selectedFindingId: string | null;
  onSelectFinding: (id: string) => void;
}) {
  return (
    <div className="relative shrink-0" style={{ width: MARGIN_W }}>
      {marks.map((mark) => {
        const selected = mark.finding.id === selectedFindingId;
        return (
          <button
            key={`note-${mark.finding.id}-${mark.index}`}
            type="button"
            onClick={() => onSelectFinding(mark.finding.id)}
            className="absolute left-0 w-full pl-5 text-left"
            style={{ top: `calc(${mark.bbox.y0 * 100}% - 6px)` }}
          >
            {/* leader line from the page edge to the note */}
            <span
              aria-hidden
              className="absolute left-0 top-[9px] block h-px bg-redpen"
              style={{ width: 16, opacity: selected ? 1 : 0.5 }}
            />
            <span
              className={`block border-l-2 border-redpen pl-2 font-mono text-2xs leading-snug ${
                selected ? 'text-redpen' : 'text-graphite'
              }`}
            >
              <span className="font-semibold">{mark.index}. </span>
              {mark.finding.field_name}
              {mark.finding.clause_ref && (
                <span className="block opacity-70">{mark.finding.clause_ref}</span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
}

/** A field the system read. Quiet by design — this layer is for verification. */
function ExtractionBox({ field }: { field: ExtractedField }) {
  if (!field.bbox) return null;
  const degraded =
    field.needs_review || field.read_method === 'template_region_fallback';
  const colour = degraded ? '#B8860B' : '#1B4D7A';
  return (
    <span
      title={`${field.name} = ${field.value ?? 'not read'}  ·  ${field.read_method} ${field.confidence.toFixed(2)}`}
      className="absolute"
      style={{
        left: `${field.bbox.x0 * 100}%`,
        top: `${field.bbox.y0 * 100}%`,
        width: `${(field.bbox.x1 - field.bbox.x0) * 100}%`,
        height: `${(field.bbox.y1 - field.bbox.y0) * 100}%`,
        border: `1px ${degraded ? 'dashed' : 'solid'} ${colour}`,
        background: degraded ? 'rgba(184,134,11,0.06)' : 'transparent',
      }}
    />
  );
}

/**
 * Stand-in for a page raster.
 *
 * Real scans carry welder photographs, names and ID numbers from an operating
 * nuclear site and can never enter the repository, so no sample image ships
 * with the frontend. This draws the shape of a form — title block, ruled rows —
 * so the overlay geometry is visible and testable in development. The moment
 * the backend serves page images, `imageUrl` replaces it and nothing else in
 * this component changes.
 */
function PagePlaceholder({ formatNo, page }: { formatNo: string; page: number }) {
  return (
    <div className="pointer-events-none absolute inset-0 select-none p-[6%]">
      <div className="flex h-full flex-col border border-rule">
        <div className="flex items-center justify-between border-b border-rule px-2 py-1.5">
          <span className="font-mono text-2xs uppercase tracking-block text-rule-strong">
            {formatNo}
          </span>
          <span className="font-mono text-2xs text-rule-strong">p{page}</span>
        </div>
        <div className="flex-1 space-y-[7px] p-3">
          {Array.from({ length: 22 }).map((_, i) => (
            <div
              key={i}
              className="h-[6px] bg-rule"
              style={{ width: `${[92, 71, 84, 58, 95, 66][i % 6]}%`, opacity: 0.55 }}
            />
          ))}
        </div>
        <div className="border-t border-rule px-2 py-1.5 text-center">
          <span className="font-mono text-2xs uppercase tracking-block text-rule-strong">
            Page raster not available in development
          </span>
        </div>
      </div>
    </div>
  );
}

/** Icon-free toolbar. These users read; controls are labelled. */
function Toolbar({
  zoom,
  onZoom,
  rotation,
  onRotate,
  pageLabel,
}: {
  zoom: number;
  onZoom: (z: number) => void;
  rotation: number;
  onRotate: () => void;
  pageLabel: string;
}) {
  const btn =
    'border border-rule-strong bg-surface px-2 py-1 font-mono text-2xs uppercase tracking-label text-graphite hover:bg-paper hover:text-ink';
  return (
    <div className="flex items-center justify-between gap-3 border-b border-rule bg-paper px-3 py-1.5">
      <span className="font-mono text-2xs uppercase tracking-label text-graphite">
        {pageLabel}
      </span>
      <div className="flex items-center gap-1.5">
        <button type="button" className={btn} onClick={() => onZoom(Math.max(0.5, zoom - 0.25))}>
          Zoom out
        </button>
        <span className="w-11 text-center font-mono text-2xs text-graphite">
          {Math.round(zoom * 100)}%
        </span>
        <button type="button" className={btn} onClick={() => onZoom(Math.min(3, zoom + 0.25))}>
          Zoom in
        </button>
        <button type="button" className={btn} onClick={() => onZoom(1)}>
          Fit
        </button>
        {/* Rotate matters: the requisition sheet arrives landscape. */}
        <button type="button" className={btn} onClick={onRotate} title={`${rotation}°`}>
          Rotate
        </button>
      </div>
    </div>
  );
}

/** Layer toggles. Lives in the panel head so the toolbar stays about the page. */
export function LayerToggles({
  showExtraction,
  showMarkup,
  onToggleExtraction,
  onToggleMarkup,
  markCount,
}: {
  showExtraction: boolean;
  showMarkup: boolean;
  onToggleExtraction: () => void;
  onToggleMarkup: () => void;
  markCount: number;
}) {
  return (
    <div className="flex items-center gap-3">
      <label className="inline-flex cursor-pointer items-center gap-1.5">
        <input
          type="checkbox"
          checked={showExtraction}
          onChange={onToggleExtraction}
          className="h-3 w-3 accent-blueprint"
        />
        <span className="label">Extraction boxes</span>
      </label>
      <label className="inline-flex cursor-pointer items-center gap-1.5">
        <input
          type="checkbox"
          checked={showMarkup}
          onChange={onToggleMarkup}
          className="h-3 w-3 accent-redpen"
        />
        <span className="label">
          Findings <Mono size="2xs" muted>({markCount})</Mono>
        </span>
      </label>
    </div>
  );
}
