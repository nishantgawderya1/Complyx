import { useCallback, useRef, useState } from 'react';
import {
  SLOT_FORMAT,
  SLOT_LABEL,
  SOURCE_SLOTS,
  type SourceSlot,
  type UploadedFile,
} from '@/lib/types';
import { Mono, TitleBlock } from '@/components/primitives/Text';
import { Button } from '@/components/primitives/Button';

/**
 * Intake — three source documents in.
 *
 * A package arrives as a batch, so this takes several files at once and works
 * out where each one belongs by reading its format number. The three slots are
 * shown filled or empty from the first paint, because **what is missing is as
 * important as what is present**: an inspector must never discover halfway
 * through a review that the lab report was never uploaded.
 *
 * Three rules, all of them consequences of "never guess quietly":
 *
 *   - A file whose format number does not resolve lands in the unplaced tray
 *     marked TEMPLATE UNKNOWN. It is never dropped into the slot it probably
 *     belongs to.
 *   - The mangled format number the classifier actually read is shown, not
 *     tidied up. If it read `NPCIL/OMD/TE. 114(R0)` the inspector sees that,
 *     because that is what makes a misclassification noticeable.
 *   - A slot can be assigned by hand, but doing so is an explicit act that is
 *     recorded -- not a silent fallback.
 */

interface IntakeProps {
  files: UploadedFile[];
  onFiles: (files: File[]) => void;
  onAssign: (filename: string, slot: SourceSlot) => void;
  onRemove: (filename: string) => void;
  onContinue: () => void;
}

export function Intake({ files, onFiles, onAssign, onRemove, onContinue }: IntakeProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const placed = new Map<SourceSlot, UploadedFile>();
  files.forEach((f) => {
    if (f.slot) placed.set(f.slot, f);
  });
  const unplaced = files.filter((f) => !f.slot);
  const ready = SOURCE_SLOTS.every((s) => placed.has(s));

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      setDragging(false);
      onFiles(Array.from(event.dataTransfer.files));
    },
    [onFiles],
  );

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-6">
      <div className="mb-5 max-w-[74ch]">
        <h2 className="font-cond text-lg font-semibold text-ink">
          Upload the three source documents
        </h2>
        <p className="mt-1 font-sans text-sm text-graphite">
          Complyx reads the actual values from these, applies the Section IX
          rules, and drafts the qualified range. It does not transcribe a WPQR —
          it builds one, and every value it writes stays traceable to the page
          it came from.
        </p>
      </div>

      {/* ---- drop zone ---- */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`mb-6 border-2 border-dashed px-6 py-8 text-center transition-colors duration-120 ${
          dragging ? 'border-blueprint bg-blueprint-soft' : 'border-rule-strong bg-surface'
        }`}
      >
        <p className="font-sans text-sm text-ink">
          Drop the requisition, weld data record and lab report here
        </p>
        <p className="mt-1 font-sans text-xs text-graphite">
          PDF only. All three at once is fine — each is placed by its format number.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          multiple
          className="sr-only"
          onChange={(e) => {
            onFiles(Array.from(e.target.files ?? []));
            e.target.value = '';
          }}
        />
        <Button className="mt-3" onClick={() => inputRef.current?.click()}>
          Choose files
        </Button>
      </div>

      {/* ---- the three slots ---- */}
      <div className="mb-2 flex items-baseline justify-between">
        <span className="label">Package slots</span>
        <Mono size="xs" muted>
          {placed.size} of 3 placed
        </Mono>
      </div>

      <div className="mb-6 border border-rule">
        {SOURCE_SLOTS.map((slot, i) => (
          <SlotRow
            key={slot}
            slot={slot}
            file={placed.get(slot)}
            last={i === SOURCE_SLOTS.length - 1}
            onRemove={onRemove}
          />
        ))}
      </div>

      {/* ---- unplaced tray ---- */}
      {unplaced.length > 0 && (
        <div className="mb-6">
          <div className="label mb-2">
            Unplaced — {unplaced.length} file{unplaced.length > 1 ? 's' : ''}
          </div>
          <div className="border border-pencil bg-pencil-soft">
            {unplaced.map((file) => (
              <div
                key={file.filename}
                className="flex flex-wrap items-center justify-between gap-3 border-b border-rule px-3 py-2.5 last:border-b-0"
              >
                <div className="min-w-0">
                  <div className="truncate font-sans text-sm text-ink">
                    {file.filename}
                  </div>
                  <div className="mt-0.5 font-mono text-2xs text-graphite">
                    {file.raw_format_text ? (
                      <>read: “{file.raw_format_text}”</>
                    ) : (
                      <>no format number found on any page</>
                    )}
                  </div>
                  {file.reason && (
                    <div className="mt-0.5 max-w-[60ch] font-sans text-xs text-pencil">
                      {file.reason}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1.5">
                  <label className="label" htmlFor={`assign-${file.filename}`}>
                    Place in
                  </label>
                  <select
                    id={`assign-${file.filename}`}
                    defaultValue=""
                    onChange={(e) =>
                      e.target.value &&
                      onAssign(file.filename, e.target.value as SourceSlot)
                    }
                    className="border border-rule-strong bg-surface px-2 py-1 font-sans text-sm text-ink"
                  >
                    <option value="" disabled>
                      Select slot…
                    </option>
                    {SOURCE_SLOTS.filter((s) => !placed.has(s)).map((s) => (
                      <option key={s} value={s}>
                        {SLOT_LABEL[s]}
                      </option>
                    ))}
                  </select>
                  <Button variant="quiet" onClick={() => onRemove(file.filename)}>
                    Remove
                  </Button>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-2 max-w-[70ch] font-sans text-xs text-graphite">
            Complyx could not place these from their format number, so it has not
            guessed. Placing one by hand is recorded against the draft as a
            manual assignment.
          </p>
        </div>
      )}

      <div className="flex items-center justify-between gap-4 border-t border-rule-strong pt-4">
        <span className="font-sans text-sm text-graphite">
          {ready
            ? 'All three sources placed. Values can be extracted.'
            : `Waiting for ${SOURCE_SLOTS.filter((s) => !placed.has(s))
                .map((s) => SLOT_LABEL[s].toLowerCase())
                .join(' and ')}.`}
        </span>
        <Button variant="primary" disabled={!ready} onClick={onContinue}>
          Extract values
        </Button>
      </div>
    </div>
  );
}

function SlotRow({
  slot,
  file,
  last,
  onRemove,
}: {
  slot: SourceSlot;
  file?: UploadedFile;
  last: boolean;
  onRemove: (filename: string) => void;
}) {
  const filled = Boolean(file);
  return (
    <div
      className={`grid grid-cols-[14px_1fr_auto] items-start gap-3 px-3 py-3 ${
        last ? '' : 'border-b border-rule'
      } ${filled ? 'bg-surface' : 'bg-paper'}`}
    >
      {/* Filled or hollow, the same square used across the product. */}
      <span
        className={`mt-1 h-3 w-3 ${
          filled ? 'border border-ink bg-ink' : 'border border-rule-strong'
        }`}
        aria-hidden
      />

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-cond text-base font-semibold text-ink">
            {SLOT_LABEL[slot]}
          </span>
          <TitleBlock formatNo={SLOT_FORMAT[slot]} />
        </div>

        {file ? (
          <>
            <div className="mt-1 truncate font-sans text-sm text-graphite">
              {file.filename}
            </div>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1">
              <Mono size="2xs" muted>
                {file.page_count} page{file.page_count === 1 ? '' : 's'}
              </Mono>
              <Mono size="2xs" muted>
                {(file.size_bytes / 1024).toFixed(0)} KB
              </Mono>
              {file.raw_format_text && (
                <Mono size="2xs" muted title="Exactly as the classifier read it">
                  read: “{file.raw_format_text}”
                </Mono>
              )}
            </div>
          </>
        ) : (
          <div className="mt-1 font-sans text-sm text-pencil">
            Not uploaded — the draft cannot be built without it
          </div>
        )}
      </div>

      {file && (
        <Button variant="quiet" onClick={() => onRemove(file.filename)}>
          Replace
        </Button>
      )}
    </div>
  );
}
