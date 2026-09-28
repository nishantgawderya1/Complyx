import { Link } from 'react-router-dom';
import { Mono } from '@/components/primitives/Text';

const WORKFLOW = [
  ['01', 'Upload the source documents', 'Requisition, weld data record and lab report arrive as one package.'],
  ['02', 'Read values with provenance', 'Every value keeps its document, page, region and read method attached.'],
  ['03', 'Derive the qualification range', 'Section IX rules produce the range; blocked inputs stay visibly blocked.'],
  ['04', 'Issue with human sign-off', 'The record is printable only after row-level review and named attestation.'],
] as const;

const SIGNALS = [
  ['No silent guesses', 'Unknown templates, disputed checkboxes and missing fields stop the flow.'],
  ['Built for inspectors', 'Dense ruled views, monospace values and document-first evidence.'],
  ['Audit-ready output', 'Rule versions, source files, manual entries and signatures stay visible.'],
] as const;

const OUTCOMES = [
  ['3', 'source documents', 'Requisition, WDR and lab report'],
  ['0', 'silent fallbacks', 'Unknown or disputed inputs are marked'],
  ['1', 'defensible record', 'Every signed value has evidence'],
] as const;

const CHECKS = [
  ['Cross-document agreement', 'Coupon, welder, WPS, position, material and dates agree before derivation starts.'],
  ['Section IX derivation', 'P-number, F-number, position, backing, progression and thickness stay tied to rule references.'],
  ['Human review points', 'Checkbox conflicts, unknown templates and blocked rules require an explicit reviewer decision.'],
  ['Issued-record provenance', 'Source versions, rule table version, manual entries and sign-off names remain on the record.'],
] as const;

const DEPLOYMENT = [
  ['On-premise friendly', 'Self-hosted fonts, quiet network assumptions and document retention controls for restricted sites.'],
  ['Reviewer-owned rules', 'Unverified rule rows remain visibly unverified until a qualified reviewer signs them.'],
  ['No black-box verdicts', 'A finding always points to the field, page, observed value and expected value.'],
] as const;

export function Landing() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="sticky top-0 z-30 border-b border-rule bg-paper/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <Link to="/" className="group">
            <div className="font-cond text-lg font-semibold leading-none text-ink">
              ComplyX
            </div>
            <div className="titleblock mt-1">ASME Sec. IX</div>
          </Link>

          <nav className="hidden items-center gap-6 md:flex" aria-label="Landing">
            <a href="#workflow" className="font-sans text-sm text-graphite hover:text-ink">
              Workflow
            </a>
            <a href="#evidence" className="font-sans text-sm text-graphite hover:text-ink">
              Evidence
            </a>
            <a href="#control" className="font-sans text-sm text-graphite hover:text-ink">
              Control
            </a>
            <a href="#checks" className="font-sans text-sm text-graphite hover:text-ink">
              Checks
            </a>
            <a href="#deployment" className="font-sans text-sm text-graphite hover:text-ink">
              Deploy
            </a>
          </nav>

          <Link
            to="/dashboard"
            className="border border-rule-strong bg-surface px-3 py-1.5 font-sans text-sm font-medium text-ink transition-colors duration-120 hover:bg-white"
          >
            Dashboard
          </Link>
        </div>
      </header>

      <main>
        <section className="relative isolate overflow-hidden border-b border-rule-strong">
          <AuditBackdrop />
          <div className="mx-auto grid min-h-[78vh] max-w-7xl content-center px-6 py-16">
            <div className="max-w-3xl">
              <div className="label mb-3">Welder qualification records, made auditable</div>
              <h1 className="font-cond text-[42px] font-semibold leading-[0.95] text-ink md:text-[76px]">
                ComplyX builds WPQRs from evidence, not assumptions.
              </h1>
              <p className="mt-5 max-w-2xl font-sans text-lg text-graphite">
                Upload the source documents, reconcile what they state, derive the
                qualified range under Section IX, and issue a record a reviewer can
                defend line by line.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-3">
                <a
                  href="mailto:demo@complyx.local?subject=ComplyX demo request"
                  className="border border-blueprint bg-blueprint px-5 py-2.5 font-sans text-sm font-medium text-white transition-colors duration-120 hover:bg-[#163F63] active:translate-y-px"
                >
                  Request demo
                </a>
                <Link
                  to="/dashboard"
                  className="border border-rule-strong bg-surface px-5 py-2.5 font-sans text-sm font-medium text-ink transition-colors duration-120 hover:bg-white active:translate-y-px"
                >
                  Dashboard
                </Link>
              </div>
            </div>
          </div>
        </section>

        <ProofStrip />

        <section id="workflow" className="border-b border-rule bg-surface">
          <div className="mx-auto grid max-w-7xl gap-8 px-6 py-14 lg:grid-cols-[0.8fr_1.2fr]">
            <div>
              <div className="label mb-2">Product loop</div>
              <h2 className="font-cond text-xl font-semibold text-ink">
                A quiet workflow for serious paperwork.
              </h2>
            </div>
            <div className="border-y border-rule-strong">
              {WORKFLOW.map(([step, title, text], index) => (
                <div
                  key={step}
                  className={`grid gap-4 py-4 md:grid-cols-[72px_0.7fr_1fr] ${
                    index === WORKFLOW.length - 1 ? '' : 'border-b border-rule'
                  }`}
                >
                  <Mono size="xs" muted>
                    {step}
                  </Mono>
                  <div className="font-sans text-sm font-medium text-ink">{title}</div>
                  <p className="font-sans text-sm text-graphite">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="evidence" className="border-b border-rule bg-paper">
          <div className="mx-auto grid max-w-7xl gap-8 px-6 py-14 lg:grid-cols-[1fr_1fr]">
            <div className="max-w-xl">
              <div className="label mb-2">Evidence first</div>
              <h2 className="font-cond text-xl font-semibold text-ink">
                Every answer carries its source.
              </h2>
              <p className="mt-3 font-sans text-sm text-graphite">
                ComplyX keeps the exact value, page location, rule reference and
                reviewer decision together. The interface is designed so uncertainty
                is seen early, not cleaned up later.
              </p>
            </div>
            <EvidencePanel />
          </div>
        </section>

        <section id="checks" className="border-b border-rule bg-surface">
          <div className="mx-auto grid max-w-7xl gap-8 px-6 py-14 lg:grid-cols-[0.95fr_1.05fr]">
            <MarkedDocument />
            <div>
              <div className="label mb-2">What ComplyX checks</div>
              <h2 className="font-cond text-xl font-semibold text-ink">
                The right interruptions, early enough to matter.
              </h2>
              <p className="mt-3 max-w-xl font-sans text-sm text-graphite">
                The product is not trying to make paperwork look easy. It is built
                to expose the exact places where a qualification record can become
                indefensible.
              </p>
              <div className="mt-6 border-y border-rule-strong">
                {CHECKS.map(([title, text]) => (
                  <div key={title} className="grid gap-3 border-b border-rule py-4 last:border-b-0 md:grid-cols-[0.55fr_1fr]">
                    <div className="font-sans text-sm font-medium text-ink">{title}</div>
                    <p className="font-sans text-sm text-graphite">{text}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="control" className="border-b border-rule bg-paper">
          <div className="mx-auto grid max-w-7xl gap-8 px-6 py-14 lg:grid-cols-[0.8fr_1.2fr]">
            <div>
              <div className="label mb-2">Why it feels different</div>
              <h2 className="font-cond text-xl font-semibold text-ink">
                Minimal on purpose. Exact where it matters.
              </h2>
            </div>
            <div className="grid gap-px border border-rule bg-rule md:grid-cols-3">
              {SIGNALS.map(([title, text]) => (
                <div key={title} className="bg-surface px-4 py-4">
                  <div className="font-sans text-sm font-medium text-ink">{title}</div>
                  <p className="mt-2 font-sans text-sm text-graphite">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="deployment" className="border-b border-rule-strong bg-surface">
          <div className="mx-auto grid max-w-7xl gap-8 px-6 py-14 lg:grid-cols-[0.8fr_1.2fr]">
            <div>
              <div className="label mb-2">Deployment posture</div>
              <h2 className="font-cond text-xl font-semibold text-ink">
                Designed for places where documents cannot drift.
              </h2>
            </div>
            <div className="grid gap-px border border-rule bg-rule">
              {DEPLOYMENT.map(([title, text]) => (
                <div key={title} className="grid gap-3 bg-surface px-4 py-4 md:grid-cols-[0.45fr_1fr]">
                  <div className="font-sans text-sm font-medium text-ink">{title}</div>
                  <p className="font-sans text-sm text-graphite">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <FinalCta />
      </main>

      <Footer />
    </div>
  );
}

function ProofStrip() {
  return (
    <section className="border-b border-rule bg-ink text-white">
      <div className="mx-auto grid max-w-7xl gap-px bg-[#3A3A35] px-6 py-px md:grid-cols-3">
        {OUTCOMES.map(([value, label, note]) => (
          <div key={label} className="bg-ink px-4 py-5">
            <div className="font-cond text-xl font-semibold leading-none text-white">
              {value}
            </div>
            <div className="label mt-2 text-rule-strong">{label}</div>
            <p className="mt-1 font-sans text-sm text-rule">{note}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function AuditBackdrop() {
  return (
    <div aria-hidden className="absolute inset-0 -z-10 opacity-95">
      <div className="absolute inset-y-0 right-0 hidden w-[62%] bg-surface lg:block" />
      <div className="absolute right-[7%] top-16 hidden w-[560px] border border-rule-strong bg-surface shadow-panel lg:block">
        <div className="border-b-2 border-ink px-4 py-3">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="font-cond text-base font-semibold uppercase text-ink">
                Welder Performance Qualification Record
              </div>
              <div className="mt-1 font-mono text-2xs text-graphite">
                FQ/069 Rev.2 - ASME BPVC.IX-2021
              </div>
            </div>
            <div className="titleblock text-right">WQT-139</div>
          </div>
        </div>
        <div className="grid grid-cols-[1fr_1.1fr_1.5fr] border-b border-rule bg-paper px-3 py-2">
          <span className="label">Variable</span>
          <span className="label">Actual</span>
          <span className="label">Range qualified</span>
        </div>
        {[
          ['Base metal P-number', 'P1 to P1', 'P1 through P15F'],
          ['Filler metal F-number', 'F-No. 4', 'F-No. 4 with and without backing'],
          ['Position', '3G uphill', 'Plate and pipe over 610mm OD'],
          ['Thickness', '16 mm', 'Cannot derive - rule row not signed'],
        ].map(([variable, actual, range], index) => (
          <div
            key={variable}
            className={`grid grid-cols-[1fr_1.1fr_1.5fr] border-l-3 px-3 py-3 ${
              index === 3 ? 'border-l-pencil bg-pencil-soft' : 'border-l-blueprint bg-surface'
            } ${index === 3 ? '' : 'border-b border-rule'}`}
          >
            <span className="font-sans text-sm text-ink">{variable}</span>
            <Mono size="xs" muted={index !== 3}>
              {actual}
            </Mono>
            <Mono size="xs" className={index === 3 ? 'text-pencil' : 'text-blueprint'}>
              {range}
            </Mono>
          </div>
        ))}
      </div>
      <div className="absolute bottom-8 left-6 right-6 h-px bg-rule-strong" />
    </div>
  );
}

function EvidencePanel() {
  return (
    <div className="border border-rule-strong bg-surface">
      <div className="flex items-center justify-between border-b border-rule bg-paper px-3 py-2">
        <span className="label">Evidence chain</span>
        <span className="titleblock">anchored 0.94</span>
      </div>
      <div className="divide-y divide-rule">
        {[
          ['Source', 'Weld data record', 'p1 - Coupon no. - WQT-139'],
          ['Rule', 'QW-423.1', 'P1 to P1 qualifies P1 through P15F'],
          ['Review', 'Signed by RK', 'Row accepted on 2026-09-28'],
        ].map(([label, value, note]) => (
          <div key={label} className="grid gap-3 px-3 py-3 md:grid-cols-[96px_1fr_1.2fr]">
            <span className="label">{label}</span>
            <Mono size="xs">{value}</Mono>
            <span className="font-sans text-sm text-graphite">{note}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MarkedDocument() {
  return (
    <div className="border border-rule-strong bg-paper p-4">
      <div className="bg-surface shadow-float">
        <div className="flex items-start justify-between border-b-2 border-ink px-4 py-3">
          <div>
            <div className="font-cond text-base font-semibold uppercase text-ink">
              Package review
            </div>
            <div className="mt-1 font-mono text-2xs text-graphite">
              exact field, exact region, exact decision
            </div>
          </div>
          <div className="titleblock text-right">WQT-139</div>
        </div>
        <div className="relative h-[360px] overflow-hidden p-5">
          <div className="absolute left-5 top-8 h-[270px] w-[62%] border border-rule bg-paper p-4">
            {Array.from({ length: 14 }).map((_, index) => (
              <div
                key={index}
                className="mb-3 h-1.5 bg-rule"
                style={{ width: [88, 62, 74, 46, 91, 68, 79][index % 7] + '%' }}
              />
            ))}
            <div className="absolute left-[58%] top-[42%] h-7 w-[27%] border-2 border-redpen bg-redpen-soft" />
            <div className="absolute left-[25%] top-[61%] h-6 w-[38%] border border-blueprint bg-blueprint-soft" />
          </div>
          <div className="absolute right-5 top-12 w-[31%] border-l-2 border-redpen pl-3">
            <div className="font-mono text-2xs font-semibold uppercase tracking-label text-redpen">
              Finding
            </div>
            <p className="mt-1 font-sans text-sm text-ink">
              Identity card carries WQT-138. Package expects WQT-139.
            </p>
          </div>
          <div className="absolute bottom-6 right-5 w-[38%] border-l-2 border-blueprint pl-3">
            <div className="font-mono text-2xs font-semibold uppercase tracking-label text-blueprint">
              Evidence
            </div>
            <p className="mt-1 font-sans text-sm text-graphite">
              WDR p1 and lab report p1 agree on WQT-139.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function FinalCta() {
  return (
    <section className="bg-paper">
      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-14 lg:grid-cols-[1fr_auto] lg:items-end">
        <div className="max-w-2xl">
          <div className="label mb-2">Start with the real workflow</div>
          <h2 className="font-cond text-xl font-semibold text-ink">
            See the WPQR builder before anything gets abstract.
          </h2>
          <p className="mt-3 font-sans text-sm text-graphite">
            The demo opens on the working dashboard: three source documents in,
            one auditable qualification record out.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <a
            href="mailto:demo@complyx.local?subject=ComplyX demo request"
            className="border border-blueprint bg-blueprint px-5 py-2.5 font-sans text-sm font-medium text-white transition-colors duration-120 hover:bg-[#163F63] active:translate-y-px"
          >
            Request demo
          </a>
          <Link
            to="/dashboard"
            className="border border-rule-strong bg-surface px-5 py-2.5 font-sans text-sm font-medium text-ink transition-colors duration-120 hover:bg-white active:translate-y-px"
          >
            Dashboard
          </Link>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-rule-strong bg-ink text-rule">
      <div className="mx-auto grid max-w-7xl gap-8 px-6 py-8 md:grid-cols-[1fr_auto_auto]">
        <div>
          <div className="font-cond text-lg font-semibold leading-none text-white">
            ComplyX
          </div>
          <p className="mt-2 max-w-md font-sans text-sm text-rule">
            Evidence-led WPQR generation and welder qualification review for
            inspection teams that need records to survive scrutiny.
          </p>
        </div>
        <div>
          <div className="label mb-2 text-rule-strong">Product</div>
          <div className="flex flex-col gap-1 font-sans text-sm">
            <a href="#workflow" className="hover:text-white">Workflow</a>
            <a href="#checks" className="hover:text-white">Checks</a>
            <Link to="/dashboard" className="hover:text-white">Dashboard</Link>
          </div>
        </div>
        <div>
          <div className="label mb-2 text-rule-strong">Record</div>
          <div className="font-mono text-2xs uppercase tracking-label text-rule">
            ASME Sec. IX<br />
            FQ/069 Rev.2<br />
            On-premise ready
          </div>
        </div>
      </div>
    </footer>
  );
}
