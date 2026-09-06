import { DOC_LABEL, DOC_ORDER, type DocType } from '@/lib/types';

/**
 * Package completeness as six squares, filled or hollow.
 *
 * The domain supplies its own visual language: a package is six documents, and
 * six marks read faster than "4/6" in a dense table row scanned at forty rows.
 * The squares are in fixed document order, so position carries meaning -- the
 * fourth square is always the lab report, whether or not it is present.
 *
 * A hollow square is absence, not "not yet checked". That distinction is the
 * whole point: missing documents must be as visible as present ones.
 */
export function DocSquares({
  present,
  size = 9,
}: {
  present: DocType[];
  size?: number;
}) {
  const has = new Set(present);
  return (
    <span
      className="inline-flex items-center gap-1"
      role="img"
      aria-label={`${present.length} of 6 documents present: ${present
        .map((d) => DOC_LABEL[d])
        .join(', ')}`}
    >
      {DOC_ORDER.map((doc) => (
        <span
          key={doc}
          title={`${DOC_LABEL[doc]} — ${has.has(doc) ? 'present' : 'missing'}`}
          style={{ width: size, height: size }}
          className={
            has.has(doc)
              ? 'border border-ink bg-ink'
              : 'border border-rule-strong bg-transparent'
          }
        />
      ))}
      <span className="sr-only">{present.length} of 6</span>
    </span>
  );
}

/**
 * The same idea at label size, for headers where the count needs to be read
 * rather than scanned.
 */
export function CompletenessLine({ present }: { present: DocType[] }) {
  const missing = DOC_ORDER.filter((d) => !present.includes(d));
  return (
    <span className="inline-flex items-center gap-2">
      <DocSquares present={present} />
      <span className="font-mono text-xs text-graphite">
        {present.length} of 6
      </span>
      {missing.length > 0 && (
        <span className="font-mono text-xs text-pencil">
          missing: {missing.map((d) => DOC_LABEL[d]).join(', ')}
        </span>
      )}
    </span>
  );
}
