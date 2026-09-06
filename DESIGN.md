# DESIGN.md — Complyx

A creative brief for the Complyx interface. Written for a designer or an AI
builder. Everything here is a decision with a reason behind it, not a preference.

---

## 1. Context

Complyx audits welder qualification packages against ASME Section IX. A package
is six documents that must agree with each other and with the code. The system
extracts values, reconciles them across documents, derives the qualified range,
and surfaces disagreements. A human confirms every finding.

**Who uses it:** QA engineers and Level II/III inspectors at nuclear and heavy
industrial sites. Tata Projects, NPCIL, L&T, Bureau Veritas. People who have spent
twenty years signing their name on documents that matter.

**What they must feel in three seconds:** this was built by someone who has held
a QA folder. Not by a startup that read about welding on the internet.

**The objective:** trust, then speed. An inspector who does not trust the tool
will re-check everything by hand and the product is worthless. Trust comes first,
and it is built through provenance, restraint, and never overstating certainty.

---

## 2. Creative direction

> **Engineering drawing title block + laboratory record book + an inspector's red
> pen.**

This is not a SaaS dashboard. It is a digital instance of a document the user
already knows how to read.

The physical objects this lives among: a stamped drawing, a bound test log, a
punch-ID witness signature, a rubber seal on a lab report, a red-pen markup on a
print. The interface should sit naturally next to those, not next to Notion.

**Restraint over expression.** Every decorative choice costs credibility here. The
interface earns interest through density, precision and typographic control, not
through motion or colour.

**If it were a physical object:** a hardback laboratory notebook with a printed
grid, an index tab per section, and correction marks in red ink.

---

## 3. Visual language

### Light, not dark

Reverse the default. The reason is functional, not aesthetic.

Inspectors work against scanned white documents all day. A dark chrome wrapped
around a white scan produces a hard luminance edge at every document boundary,
which is the exact condition that causes eye strain over an eight-hour review
session. It also visually separates the tool from the artifact, when the goal is
for them to feel continuous.

A paper-toned interface holding a paper document reads as one surface.

### Colour

Drawn from the drafting table, not from a design system.

| Role | Value | Where it appears |
|---|---|---|
| Page ground | `#F7F5F0` warm paper | Application background |
| Surface | `#FFFFFF` | Document canvas, cards, tables |
| Rule / grid | `#DDD8CE` | Hairlines, table borders, grid marks |
| Ink | `#1A1A18` near-black | Primary text |
| Graphite | `#6B6A65` | Secondary text, metadata, labels |
| Blueprint | `#1B4D7A` | Structural accent, active nav, links, headers |
| Red pen | `#C1392B` | Findings, discrepancies, corrections. **Nothing else.** |
| Stamp | `#2D6A4F` | Confirmed, verified, cleared |
| Pencil | `#B8860B` muted ochre | Review required, uncertain, unverified rule |

Two rules on colour, both absolute:

**Red is reserved for findings.** Not for delete buttons, not for required-field
asterisks, not for error toasts about network failures. When an inspector sees
red on this screen it means the system found a discrepancy in the documents.
Diluting that is the single fastest way to make the tool ignorable.

**No gradients anywhere.** Not on buttons, not on headers, not as background
washes. Flat ink on flat paper.

### Typography

**IBM Plex.** The whole family. Chosen deliberately, not as a default.

Plex was drawn for an engineering institution. It has the slightly mechanical
joints and open apertures of technical lettering without tipping into pastiche.
It carries institutional weight, which is exactly the register this product needs.
And it is not the font every generated interface arrives wearing.

| Use | Face |
|---|---|
| Screen titles, section heads | IBM Plex Sans Condensed, 600 |
| Body, descriptions, prose | IBM Plex Sans, 400/500 |
| Every value, ID, code, date, measurement | IBM Plex Mono, 400/500 |
| Form labels, table headers, metadata | IBM Plex Sans, 500, uppercase, letterspaced +0.06em, 11px |

**The monospace rule is absolute.** Coupon numbers, welder IDs, WPS numbers, heat
numbers, format numbers, P-numbers, F-numbers, clause references, thicknesses,
currents, voltages, dates. All monospace. This is not styling. Monospace makes
character-level differences visible, and `TPL/GHAVP/W-71` versus `TPL/GHAVP/W-72`
is exactly the kind of difference this product exists to catch.

**Scale:** compressed. 11 / 12 / 13 / 15 / 20 / 28. No 48px headlines. This is a
working instrument, and inspectors reviewing forty packages want density, not air.

### Shape, border, shadow

**Sharp.** Border radius 0 to 2px. Nothing rounder. Forms have corners.

**Borders carry the structure.** 1px hairlines in `#DDD8CE` do the work that
shadows do elsewhere. Tables use ruled lines like a printed form, not floating
cards with gaps between them.

**Shadow is almost absent.** One level only, `0 1px 2px rgba(26,26,24,0.06)`, and
only on genuinely floating layers: modals, dropdowns. Never on cards or panels.

**Texture:** a barely visible paper grain on the page ground, at most 2% opacity.
Optional. If it reads as an effect, remove it.

---

## 4. Signature concept: the inspector's markup

**Findings appear as red-pen annotations on the document itself.**

Every extracted value carries a bounding box from the page it came from. When the
system finds a discrepancy, it draws on the scan the way an inspector would draw
on a print: a red rectangle around the value, a short handwritten-position note in
the margin, a leader line where the note sits away from the mark.

Not a callout bubble. Not a tooltip. A mark on the document.

This concept appears at full strength on the document viewer, and echoes
elsewhere:

- The package index is a **row of tabs on a folder**, one per document type,
  missing documents shown as an empty tab slot rather than hidden
- The derivation screen uses the **WPQR's own two-column structure**, because that
  structure already encodes the meaning
- Confirmed findings get a **stamp treatment**: a small rotated outline mark with
  initials and date, the way a witness signs off

One concept, applied consistently. No second visual gimmick.

---

## 5. Information hierarchy

What an inspector opening a package must see, in order:

1. **Which package.** Coupon number and welder, monospace, large, immediate.
2. **Is it clean.** One line: findings count by severity, or "no findings".
3. **What is wrong.** The findings themselves, red, with clause references.
4. **Where it came from.** The document and the exact region.
5. **What is missing.** Package completeness.
6. **Confirm.** The action, deliberate and unmissable.

The screen must answer "is this package clean" before the user scrolls. Everything
else is detail behind that answer.

---

## 6. Screen inventory

### Entry

**1. Login.** Single centred column on paper ground. Wordmark, two fields, one
button. No illustration, no marketing copy, no split-screen photograph. It should
feel like signing into a records system.

**2. Project selection.** If the user belongs to more than one project. A short
list, monospace project codes, client name, active package count.

### Core loop

**3. Package worklist.** The home screen and the most-used view in the product.

A dense ruled table, one row per package. Columns: coupon number, welder name and
ID, WPS, date, completeness (how many of six documents present, shown as six small
squares filled or hollow), findings summary, status.

Filter rail on the left: status, welder, WPS, date range, finding severity. Filters
are checkboxes on a ruled list, not pills.

Rows with critical findings carry a 2px red left rule. Rows awaiting confirmation
carry ochre. The table should be scannable at forty rows without scrolling on a
laptop.

**4. New package intake.** Drop zone for multiple files at once, because a package
arrives as a batch. As files land, the system classifies each one and shows what it
recognised: format number, revision, document type, and which of the six slots it
fills. Unrecognised forms land in an "unclassified" tray with a clear
`TEMPLATE UNKNOWN` mark, never silently guessed into a slot.

The screen shows the six slots filling as files are assigned, so completeness is
visible before processing begins.

**5. Processing.** A stepped log, not a spinner. Each document listed, each showing
its stage: classified, deskewed, regions read, checkboxes read, done. Page counts
visible. This takes minutes for a full package, so the wait must feel like work
happening, not like a hang. Lines complete top to bottom the way a build log does.

**6. Package detail.** The central working screen.

Header: coupon number, welder name and ID, WPS, project, dates. Monospace
throughout. Status on the right.

Below it, a folder tab row: six tabs, one per document type, each showing format
number and whether it was template-matched. Missing documents show as an empty
outlined tab, present but not clickable, so absence is as visible as presence.

Main area splits: findings list on the left, document canvas on the right. Selecting
a finding scrolls the canvas to the exact page and highlights the exact region.
Selecting a mark on the canvas selects its finding. Two-way binding is the point of
the whole screen.

**7. Document viewer.** The scan at full fidelity with the markup layer over it.

Toolbar, icon only, no labels: zoom, fit, rotate, toggle markup layer, toggle
extraction boxes. Rotate matters because the Weld Data Record arrives landscape.

Two overlay layers, independently toggleable. Extraction boxes show every field the
system read, thin blueprint outlines, quiet. Finding marks show discrepancies, red,
loud. An inspector who wants to verify one number turns the first layer on. An
inspector reviewing findings leaves only the second.

**8. Finding detail.** Opens as a panel, not a modal, so the document stays visible.

Structure: what was observed, what was expected, where each came from, which clause
governs. Documents involved are listed as chips that jump to that document at that
page. Clause reference is a link to the explanation layer.

Two actions at the bottom: confirm, or dismiss with a required reason. Dismissal
without a reason is not possible.

**9. Reconciliation view.** For cross-document findings specifically, a comparison
grid is clearer than a list.

Rows are fields (welder name, coupon number, WPS, position, thickness). Columns are
the six documents. Cells hold the value each document states. Agreement reads as a
clean row. Disagreement is immediately visible because one cell breaks the pattern,
and gets the red treatment.

This grid is where the WQT-139 welder name discrepancy becomes obvious in one
glance. It is the most persuasive screen in the product for a first demo.

**10. Derivation view.** The WPQR's own two-column form, rebuilt.

Left column: actual values, as extracted. Right column: qualified range. But the
right column splits into two sub-columns: what the system derived from the rules,
and what the WPQR as filled actually says. Where they match, quiet. Where they
diverge, red rule between them and a clause reference.

Each derived value shows its governing clause in small monospace beneath it. An
inspector must be able to see why the system says P1 through P15F, not just that it
does.

**11. Checkbox review.** A dedicated small screen for the case that matters most.

When the CV reader and the vision reader disagree on a checkbox, show the cropped
region large, both readings, and ask the human. Because the three-layer-minimum box
decides between "max to be welded" and a 2t limit, this screen deserves to exist on
its own rather than being buried in a findings list.

**12. Package confirmation.** The closing action.

A summary: findings confirmed, findings dismissed with reasons, documents included,
rule table version, template versions, model version. Then the sign-off. This screen
should feel weighty. It is the moment a human takes responsibility, and the design
should not make it feel like clicking "save".

### Registry and lookup

**13. Welder registry.** All welders on the project. Name, ID, photograph if
present on the identity card, processes qualified, positions qualified, last
qualification date, continuity status.

**14. Welder detail.** One welder's full history. Qualification records, each with
its coupon number and derived qualified range. Continuity timeline showing the
six-month QW-322 window and when it lapses.

**15. Continuity dashboard.** Who lapses when. A timeline, not a table: a horizontal
axis of weeks, welders as rows, qualification windows as bars, the lapse point
marked. Bars entering the next 30 days turn ochre. This is the screen a site QA
manager will keep open.

**16. Joint-to-welder lookup.** The field query. Inspector inputs joint parameters:
process, position, base metal P-number, thickness, pipe or plate, diameter. System
returns qualified welders. Input as a compact form, results as a ruled list. Fast,
no ceremony.

### Administration

**17. Rule table browser.** The QW tables as encoded, readable. Each entry shows its
clause reference, its values, and its verification state. Unverified entries carry a
visible ochre `UNVERIFIED` mark. A reviewer can mark an entry verified, which records
who and when.

This screen makes the product's honesty legible. An auditor asking "where did this
number come from" gets an answer.

**18. Template registry.** The known forms: format number, revision, document type,
field region map, and a sample. When an unknown form appears, this is where a new
template gets defined.

**19. Settings.** Project, team, retention policy, deployment mode. Short and plain.

### States

**20. Empty states.** No packages yet, no findings on a clean package, no welders
registered, no lapses upcoming. The clean-package state deserves care: it should
read as a positive result, a stamp mark and a plain line, not as an absence.

**21. Error states.** Unreadable file, unrecognised format, extraction failed,
provider unavailable. Each states plainly what happened and what the user can do.
Never a stack trace, never a red toast that disappears before it is read.

Critically, distinguish document problems from infrastructure problems in the
language. "This scan could not be read" is a fact about the document. "The service
is unavailable, retry" is a fact about the system. The user needs to know which.

---

## 7. Content as design material

The domain supplies its own visual language. Use it.

**Format numbers are typographic artifacts.** `NPCIL/QMD/TF-127 Rev.R0` set in
small letterspaced monospace, positioned like a drawing title block in the corner
of a document panel, does more for credibility than any illustration.

**Clause references are the product's authority.** `QW-452.1(b)` should appear
consistently, in monospace, small, immediately after any derived value. Their
constant presence is what tells the inspector this is not a guess.

**Six squares for six documents.** Package completeness as a row of small squares,
filled or hollow, readable at a glance in a dense table row.

**The stamp.** Confirmed findings get a small outline stamp mark with the confirmer's
initials and date, slightly rotated. It is the one place a deliberate imperfection
belongs, because that is how stamps land on paper.

---

## 8. Interaction and motion

**Motion philosophy: instrument, not interface.**

Movement is functional or absent. Nothing decorates.

- Panel opens: 120ms, ease-out, opacity and 4px translate. Nothing further.
- Document canvas scrolling to a finding: 200ms smooth scroll, then the mark holds
  a brief 1.5x outline weight before settling. This one exists because the eye needs
  to find the mark.
- Table rows: background shifts to `#FFFFFF` on hover. No lift, no shadow, no scale.
- Buttons: background darkens on hover, 1px inset on press. Nothing moves position.
- Processing log: lines appear as they complete. No skeleton shimmer, no progress
  bar estimating a time it cannot know.

No page transitions. No scroll-triggered reveals. No parallax. No counters animating
up. An inspector opening the same package twice should see it appear identically both
times.

`prefers-reduced-motion` removes the scroll animation and the mark emphasis. Everything
else is already still.

---

## 9. Responsive behaviour

**Desktop is the design target.** This is a two-monitor tool used at a desk. The
split document-and-findings layout needs width and should not apologise for it.

**Tablet (portrait) is a real case.** Inspectors carry tablets on site. The split
becomes a toggle: findings list or document, one at a time, with a persistent switch.
The reconciliation grid becomes horizontally scrollable with the field column frozen.
The worklist drops to coupon, welder, findings, status.

**Phone is read-only.** Do not attempt package review on a phone. What phone supports:
the continuity dashboard, the joint-to-welder lookup, and welder detail. Those three
are genuinely useful standing next to a weld. Everything else redirects with a plain
message rather than degrading into an unusable layout.

Deciding what a screen size does *not* support is a design decision, not a failure.

---

## 10. Technical requirements

- Semantic HTML. Tables are `<table>`, because they are tables.
- Keyboard navigable end to end. Inspectors reviewing forty packages will not reach
  for a mouse. Arrow keys move between findings, `c` confirms, `d` dismisses, `j`/`k`
  move rows.
- WCAG AA contrast minimum. Red pen on paper ground meets it; verify every pairing.
- Colour never carries meaning alone. Every severity has a text label beside it.
- Document canvas must handle 300 DPI page images without jank. Tile or virtualise.
- Print stylesheet for the package confirmation view. This document will be printed
  and filed.

---

## 11. What this must not become

- **A dark navy dashboard with a teal accent.** That is the generated default and it
  would make this product indistinguishable from every AI tool shipped this year.
- **Inter, DM Sans, Poppins, or Manrope.** The fonts every generated interface wears.
- **Gradient headers, glassmorphism, glow effects.** None of it survives contact with
  a QA department.
- **Rounded floating cards with gaps between them.** Forms have rules and corners.
- **Illustrated empty states.** No cartoon inspector, no isometric factory.
- **Stock photography of welders.** Especially not stock photography of welders.
- **Icon-led navigation.** These users read. Label the navigation.
- **Animated counters, progress rings, sparklines as decoration.** If a number moves,
  the user waits to read it.
- **Red used for anything except findings.**
- **A chatbot.** There is no assistant in this product. The system reports what it
  found and the human decides.

---

## 12. Final principle

**Never let the interface look more certain than the system is.**

When the system is confident, present cleanly. When it is uncertain, that uncertainty
must be visible in the design, not buried in a confidence score. An unverified rule
table entry, a template that did not match, a checkbox the two readers disagreed on:
each of these must be as visible as a finding.

The product's entire value rests on an inspector trusting it. Trust survives a system
that says "I am not sure about this one". It does not survive a system that looked
sure and was wrong.
