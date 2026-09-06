import { ScreenHead } from '@/components/primitives/Panel';
import { ClauseRef } from '@/components/primitives/Text';

/**
 * A screen that is specified but not built.
 *
 * It states what belongs here and what it depends on, rather than showing a
 * plausible-looking mock. The same discipline the backend applies to a field it
 * could not read: say so, do not present an empty shell as a working one.
 */
export function Stub({
  eyebrow,
  title,
  designRef,
  blockedBy,
  contents,
  clause,
}: {
  eyebrow: string;
  title: string;
  designRef: string;
  blockedBy: string;
  contents: string[];
  clause?: string;
}) {
  return (
    <>
      <ScreenHead
        eyebrow={eyebrow}
        title={title}
        right={clause ? <ClauseRef code={clause} /> : undefined}
      />
      <div className="min-h-0 flex-1 overflow-auto p-6">
        <div className="max-w-[74ch]">
          <div className="mb-4 border border-rule bg-surface">
            <div className="border-b border-rule bg-paper px-3 py-1.5">
              <span className="label">Not built</span>
            </div>
            <div className="px-3 py-3">
              <p className="font-sans text-sm text-ink">
                Specified in <span className="font-mono text-xs">{designRef}</span>.
              </p>
              <p className="mt-2 font-sans text-sm text-graphite">
                <span className="label">Blocked by</span>
                <br />
                {blockedBy}
              </p>
            </div>
          </div>

          <div className="label mb-2">This screen holds</div>
          <ul className="flex flex-col gap-1.5">
            {contents.map((item) => (
              <li
                key={item}
                className="border-l-2 border-rule-strong pl-3 font-sans text-sm text-graphite"
              >
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </>
  );
}
