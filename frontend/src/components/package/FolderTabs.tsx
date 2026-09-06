import {
  DOC_FORMAT,
  DOC_LABEL,
  DOC_ORDER,
  type DocType,
  type SourceDocument,
} from '@/lib/types';

/**
 * The package index, as a row of tabs on a folder.
 *
 * Six tabs in fixed document order. A missing document renders as an empty
 * outlined tab — present on screen, not clickable — so **absence is as visible
 * as presence**. Hiding a missing document would make an incomplete package
 * look complete, which is the single failure this interface must not have.
 *
 * Each tab carries its format number, set like a drawing title block, and a
 * mark when the template did not match or is not reviewer-verified.
 */
export function FolderTabs({
  documents,
  selectedId,
  onSelect,
}: {
  documents: SourceDocument[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const byType = new Map<DocType, SourceDocument>(
    documents.map((d) => [d.doc_type, d]),
  );

  return (
    <div
      className="flex items-end gap-px overflow-x-auto border-b border-rule-strong bg-paper px-4 pt-2"
      role="tablist"
      aria-label="Package documents"
    >
      {DOC_ORDER.map((type) => {
        const document = byType.get(type);
        const selected = document?.id === selectedId;

        if (!document) {
          return (
            <div
              key={type}
              role="tab"
              aria-selected={false}
              aria-disabled
              title={`${DOC_LABEL[type]} — not present in this package`}
              className="min-w-[124px] shrink-0 border border-dashed border-rule-strong border-b-0 bg-transparent px-3 py-1.5 opacity-70"
            >
              <div className="font-cond text-sm font-medium text-graphite">
                {DOC_LABEL[type]}
              </div>
              <div className="mt-0.5 font-mono text-2xs uppercase tracking-label text-pencil">
                Missing
              </div>
            </div>
          );
        }

        const flagged = !document.template_matched || !document.template_verified;

        return (
          <button
            key={type}
            role="tab"
            aria-selected={selected}
            onClick={() => onSelect(document.id)}
            className={`min-w-[124px] shrink-0 border border-b-0 px-3 py-1.5 text-left transition-colors duration-120 ${
              selected
                ? 'border-rule-strong bg-surface'
                : 'border-rule bg-paper hover:bg-white'
            }`}
            style={selected ? { marginBottom: '-1px' } : undefined}
          >
            <div
              className={`font-cond text-sm font-medium ${
                selected ? 'text-ink' : 'text-graphite'
              }`}
            >
              {DOC_LABEL[type]}
            </div>
            <div className="mt-0.5 flex items-center gap-1.5">
              <span className="titleblock truncate">
                {document.format_no || DOC_FORMAT[type]}
              </span>
              {flagged && (
                <span
                  className="shrink-0 font-mono text-2xs text-pencil"
                  title={
                    !document.template_matched
                      ? 'Template unknown — read by whole-page extraction'
                      : 'Template regions not reviewer-verified'
                  }
                >
                  {!document.template_matched ? '?' : '!'}
                </span>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
