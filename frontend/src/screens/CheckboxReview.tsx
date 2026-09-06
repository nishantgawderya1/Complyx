import { useState } from 'react';
import { CHECKBOX_CONFLICT } from '@/lib/fixtures';
import { ClauseRef, Mono } from '@/components/primitives/Text';
import { Button } from '@/components/primitives/Button';
import { ScreenHead } from '@/components/primitives/Panel';

/**
 * Checkbox review — a screen of its own, for the mark that decides the answer.
 *
 * When the OpenCV reader and the vision reader disagree, no automatic
 * resolution is permitted. The human sees the cropped region large, both
 * readings, and — critically — **what each answer would mean**, because the
 * three-layer minimum box decides between "max. to be welded" and a 2t limit.
 *
 * Showing the consequence next to the choice is the difference between asking
 * someone to read a checkbox and asking them to make a qualification decision.
 * It is the latter.
 */
export function CheckboxReview() {
  const conflict = CHECKBOX_CONFLICT;
  const [answer, setAnswer] = useState<'yes' | 'no' | null>(null);

  return (
    <>
      <ScreenHead
        eyebrow="WQT-139 · WPQR · FQ/069 Rev.2"
        title="Checkbox requires a human decision"
        right={<ClauseRef code={conflict.clause_ref} />}
      />

      <div className="min-h-0 flex-1 overflow-auto p-6">
        <div className="max-w-4xl">
          <div className="mb-4 border-l-3 border border-pencil bg-pencil-soft px-4 py-3">
            <div className="label mb-1">Readers disagree</div>
            <p className="max-w-[70ch] font-sans text-sm text-ink">
              The ink-density reader and the vision model read this box
              differently. Complyx does not resolve the conflict, because either
              resolution would be a guess with no visible symptom if it were
              wrong.
            </p>
          </div>

          {/* ---- the crop, large ---- */}
          <div className="mb-5 border border-rule bg-surface">
            <div className="flex items-center justify-between border-b border-rule bg-paper px-3 py-1.5">
              <span className="label">{conflict.label}</span>
              <span className="titleblock">
                page {conflict.page} · region{' '}
                {conflict.yes_bbox.x0.toFixed(3)},{conflict.yes_bbox.y0.toFixed(3)}
              </span>
            </div>
            <div className="flex items-center justify-center gap-8 bg-white p-8">
              <CropStandIn label="Yes" reading={conflict.cv_reading} />
              <CropStandIn label="No" reading="unchecked" />
            </div>
            <div className="border-t border-rule bg-paper px-3 py-1.5 text-center">
              <span className="titleblock">
                Region raster not available in development
              </span>
            </div>
          </div>

          {/* ---- the two readings ---- */}
          <div className="mb-5 grid grid-cols-2 gap-4">
            <ReadingCard
              reader="OpenCV ink density"
              reading={conflict.cv_reading}
              detail="Thresholded pixel coverage inside the detected rectangle"
            />
            <ReadingCard
              reader="Vision model"
              reading={conflict.vision_reading}
              detail="Cropped region, asked checked or unchecked"
            />
          </div>

          {/* ---- what each answer means ---- */}
          <div className="border border-rule bg-surface">
            <div className="border-b border-rule bg-paper px-3 py-2">
              <span className="label">What this decides</span>
            </div>
            <div className="divide-y divide-rule">
              <ChoiceRow
                value="yes"
                title="Yes — three or more layers"
                consequence={conflict.consequence_if_yes}
                selected={answer === 'yes'}
                onSelect={() => setAnswer('yes')}
              />
              <ChoiceRow
                value="no"
                title="No — fewer than three layers"
                consequence={conflict.consequence_if_no}
                selected={answer === 'no'}
                onSelect={() => setAnswer('no')}
              />
            </div>
            <div className="flex items-center justify-between gap-4 border-t border-rule bg-paper px-3 py-2.5">
              <span className="font-sans text-xs text-graphite">
                This decision is recorded against your name and cannot be applied
                in bulk.
              </span>
              <Button variant="primary" disabled={answer === null}>
                Record decision
              </Button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function CropStandIn({
  label,
  reading,
}: {
  label: string;
  reading: 'checked' | 'unchecked';
}) {
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="flex h-20 w-20 items-center justify-center border-2 border-ink">
        {reading === 'checked' && (
          <span className="font-mono text-xl font-semibold text-ink">v</span>
        )}
      </div>
      <span className="label">{label}</span>
    </div>
  );
}

function ReadingCard({
  reader,
  reading,
  detail,
}: {
  reader: string;
  reading: 'checked' | 'unchecked';
  detail: string;
}) {
  return (
    <div className="border border-rule bg-surface px-3 py-2.5">
      <div className="label mb-1">{reader}</div>
      <Mono size="base" className="font-medium">
        {reading}
      </Mono>
      <p className="mt-1 font-sans text-xs text-graphite">{detail}</p>
    </div>
  );
}

function ChoiceRow({
  value,
  title,
  consequence,
  selected,
  onSelect,
}: {
  value: string;
  title: string;
  consequence: string;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <label
      className={`flex cursor-pointer items-start gap-3 px-3 py-3 ${
        selected ? 'bg-blueprint-soft' : 'hover:bg-paper'
      }`}
    >
      <input
        type="radio"
        name="checkbox-answer"
        value={value}
        checked={selected}
        onChange={onSelect}
        className="mt-1 accent-blueprint"
      />
      <span>
        <span className="block font-sans text-sm font-medium text-ink">{title}</span>
        <span className="mt-0.5 block font-mono text-xs text-graphite">
          → {consequence}
        </span>
      </span>
    </label>
  );
}
