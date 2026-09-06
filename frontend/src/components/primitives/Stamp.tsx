/**
 * The confirmation stamp.
 *
 * A confirmed finding gets a small outline mark with the confirmer's initials
 * and date, slightly rotated. This is the one place in the interface where a
 * deliberate imperfection belongs, because that is how a stamp lands on paper.
 *
 * The rotation is derived from the confirmer's initials rather than randomised,
 * so the same sign-off renders identically every time. An inspector opening the
 * same package twice must see it appear identically both times, and a stamp
 * that wobbles on re-render would quietly break that.
 */

function angleFor(seed: string): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  }
  // -2.5deg .. +2.5deg, in half-degree steps.
  return ((Math.abs(hash) % 11) - 5) / 2;
}

export function Stamp({
  initials,
  date,
  label = 'Confirmed',
  tone = 'stamp',
}: {
  initials: string;
  date: string;
  label?: string;
  tone?: 'stamp' | 'redpen';
}) {
  const colour = tone === 'stamp' ? 'border-stamp text-stamp' : 'border-redpen text-redpen';
  return (
    <span
      className={`inline-flex flex-col items-center border-2 px-2 py-0.5 font-mono uppercase leading-tight ${colour}`}
      style={{ transform: `rotate(${angleFor(initials + date)}deg)` }}
      title={`${label} by ${initials} on ${date}`}
    >
      <span className="text-2xs font-semibold tracking-block">{label}</span>
      <span className="text-2xs tracking-label opacity-80">
        {initials} · {date}
      </span>
    </span>
  );
}

/**
 * A dismissal mark. Same object, different verdict, and it always carries the
 * reason -- dismissal without a reason is not possible in this product.
 */
export function DismissMark({
  initials,
  date,
  reason,
}: {
  initials: string;
  date: string;
  reason: string;
}) {
  return (
    <span
      className="inline-flex flex-col items-center border-2 border-graphite px-2 py-0.5 font-mono uppercase leading-tight text-graphite"
      style={{ transform: `rotate(${angleFor(initials + date)}deg)` }}
      title={`Dismissed by ${initials} on ${date}: ${reason}`}
    >
      <span className="text-2xs font-semibold tracking-block">Dismissed</span>
      <span className="text-2xs tracking-label opacity-80">
        {initials} · {date}
      </span>
    </span>
  );
}
