# CLAUDE.md — Complyx

Read this fully before writing code. It supersedes `AGENT_CONTEXT.md`, which
described an earlier scope.

Repository: `github.com/nishantgawderya1/complyx`
Commits authored as `nishantgawderya1 <nishantgawderya@gmail.com>`

---

## 1. What changed, and why it matters

The original scope was single-document Material Test Certificate auditing:
extract material property values, compare against ASTM threshold tables, return
PASS/FAIL. That engine is **built and passing 127 tests offline**. It is not
being thrown away.

But real documents arrived from an operating nuclear site (NPCIL GHAVP-1&2, Tata
Projects as contractor), and they showed the actual job is different. A welder
qualification is not one document. It is a **package of six documents that must
agree with each other and with ASME Section IX**.

The MTC engine audits one certificate against a threshold table. This audits a
package against itself and against a code. That is a different shape of problem,
and it is the more defensible product — single-document extraction is easy to
copy, package reconciliation is not.

**Current focus: ASME Section IX welder performance qualification only.** Other
sections and codes come later. Do not generalise ahead of this.

---

## 2. The document package

Six documents, one welder, one coupon number (`WQT-138`, `WQT-139`, ...).

```
Welder Qualification Requisition Sheet   NPCIL/QMD/TF/216
  who needs qualifying, process, electrode, position, P-numbers,
  pipe size / thickness, joint design
        |
        v
Weld Data Record                         NPCIL/QMD/TF-114(R0)
  actual welding parameters per pass: process, direction, filler type and
  size, travel speed, polarity, current min/max, voltage min/max, interpass
  temp, heat no, batch no, stringer/weave, visual exam result
        |
Sample Card                              NPCIL/QMD/TF053-R1
  coupon -> which lab, tests required, sample size, witnesses, punch ID
        |
        v
Lab Test Report                          SWILPL/7.8F/01 (Star Wire India)
  test parameter, method, result, requirement, conformity
        |
        v
WPQR (QW-484)                            FQ/069 Rev.2
  ACTUAL VALUES  |  QUALIFIED RANGE      <- the deliverable
        |
        v
Welder Identity Card                     NPCIL/QMD/TF-127 Rev.R0
  qualified range carried to the field
```

### The critical structural fact

The WPQR has two columns. **Actual Values** are transcribed from the three raw
documents. **Qualified Range** is not copied from anywhere — it is *derived* by
applying Section IX rules to the actual values.

That derivation is the job. It is where errors hide, because a wrong qualified
range looks exactly like a right one on paper and only surfaces when a welder
works outside their actual qualification.

---

## 3. Three check classes

Build them in this order. Each is independently valuable.

### Class 1 — Cross-document reconciliation

Pure string and value matching. No code knowledge required.

- Welder name identical across all six documents
- Coupon number (WQT-xxx) consistent
- WPS number consistent
- Position, process, electrode consistent
- Base metal spec consistent
- Thickness consistent
- Date ordering: requisition <= weld date <= sampling <= testing <= WPQR <= ID card
- Lab report number on WPQR matches the actual lab report
- Every referenced document is present in the package

**A real finding already exists in the sample set.** The Weld Data Record dated
18.03.2026 is labelled coupon `WQT-139` but names welder `AMIR CHAND CHAUDHARY`.
Every other WQT-139 document (WPQR, sample card, Star Wire report 140272) names
`Raj Narayan Prasad`. Amir Chand belongs to WQT-138, tested 28.02.2026. This is
either a real transcription error on a nuclear QA package or an OCR misread — it
must be verified against the original before being used as a test expectation.
Either way, this is exactly the class of finding the product exists to catch, and
it should be the first end-to-end test case.

### Class 2 — Section IX rule compliance

Deterministic table lookup against encoded QW clauses.

- Test type matches coupon thickness (QW-452.1: 16mm plate -> 2 side bends)
- Bend acceptance criterion correct (QW-163)
- Required signatures and witness records present
- Lab is the one named on the sample card

### Class 3 — Qualified range derivation

Compute the range from actual values, compare against what was filled in.

Rules visible in the sample WPQR:

| Actual value | Derived qualified range | Clause |
|---|---|---|
| P1 to P1 | P1 through P15F | QW-423.1 |
| F-No. 4 (E7018) | F4 with & without backing; F3, F2, F1 with backing | QW-433 |
| 16mm plate, 3+ layers checked | Max. to be welded | QW-452.1(b) |
| 3G groove, plate | Plate & pipe over 610mm OD, F & V; pipe 73-610mm OD, F; fillet F,H,V | QW-461.9 |
| Welded without backing | Qualifies with & without backing | QW-402.4 |
| Uphill progression | Uphill only | QW-405.3 |

**Naming note:** `WQT-138` / `WQT-139` are coupon numbers, not code references.
`QW-350` is the welding variables clause. `QW-484` is the WPQR form. `QW-301` is
the qualification requirement. Do not conflate these.

---

## 4. Architecture decisions — read before proposing alternatives

### These are numbered forms, not free-form documents

Every document carries a format number and revision in its header
(`NPCIL/QMD/TF-127, Rev.R0`). The same six templates repeat across every welder
package on the site.

So do **not** do general document understanding. Classify the form, look up its
template, then read only the known field regions.

```
page image
  -> deskew / orientation correction        (OpenCV + PyMuPDF)
  -> form classifier: read format no.       (cheap, header region only)
  -> template registry lookup               (TF-127-R0 -> field regions)
  -> crop each region, read that region     (vision model, small crops)
  -> field value + bounding box + confidence
```

Higher accuracy, roughly an order of magnitude lower cost, and every value
arrives with the coordinates it came from.

When the format number is unrecognised, fall back to whole-page vision
extraction and mark the document `template_unknown` so a human knows which path
produced the values. Never silently guess a template.

### Checkboxes get read twice

The "3 layers minimum: Yes/No" checkbox on the WPQR decides between
"max. to be welded" and a 2t thickness limit. It is the single most consequential
mark on the form and it is not text.

Read it two independent ways:

1. **OpenCV** — crop the box, threshold, measure ink density inside the rectangle
2. **Vision model** — crop the same region, ask checked or unchecked

Agreement -> high confidence. **Disagreement -> REVIEW, always.** Never resolve
the conflict automatically.

### A vision model is required

Text-only OCR cannot see checkbox state, cannot preserve the Actual Values vs
Qualified Range column association, and degrades badly on stamped and signed
scans. Tesseract stays only for coarse orientation detection.

`LLMClient` keeps its provider-agnostic interface but the signature changes to
accept page images alongside text. **Confirm what NVIDIA NIM actually serves
before committing to a model ID** — `nemotron-4-340b-instruct` is text-only and
dated. The interface exists precisely so this is a config change.

### No vector search on the verdict path

QW-423, QW-433, QW-451/452, QW-461.9 are **tables**: discrete inputs, discrete
outputs. Encode them as versioned rule data, same as the existing
`astm_asme.json`. Vector retrieval can return the wrong row with no visible
symptom, which is the failure mode the whole architecture is built to avoid.

`chromadb` and `langchain` are unused dead weight in `requirements.txt` and carry
a pydantic conflict risk. **Remove them.**

RAG belongs only on the explanation layer — showing an inspector the clause text
behind a finding, answering "why does 3G qualify pipe over 610mm OD". It never
decides anything. When that arrives, use `pgvector` in the existing Postgres, not
a separate service (one database, RLS already applies, nothing extra to run on an
air-gapped site).

### Background jobs must survive restarts

A six-document package is 20-40 page reads. That is minutes, not seconds.
FastAPI `BackgroundTasks` lose work silently on restart, which is unacceptable
for a nuclear QA audit.

Do not reach for Celery or Redis. A `jobs` table in Postgres plus a worker loop
polling it survives restarts, is inspectable in plain SQL, and adds one process.

---

## 5. The rule that has not changed

**AI extracts values. Deterministic code decides everything else.**

The vision model reads what is printed or marked on the form. It never derives a
qualified range, never compares a value to a rule, never emits a verdict.
Derivation and comparison are plain Python against reviewer-verified tables.

### Never guess quietly

Every layer that cannot do its job with confidence says so and routes to REVIEW:

- Field not found -> REVIEW, not "no finding"
- Checkbox readers disagree -> REVIEW
- Format number unreadable -> `template_unknown`, general extraction, flagged
- Value with no unit -> REVIEW
- Document missing from package -> incomplete, never a partial verdict
- Grade, P-number or F-number not in the rule tables -> "rule not found", never a
  near match
- Poor-quality scan -> can never produce a clean PASS

A silent partial result that looks complete is a defect, not a degraded mode.

### Human confirmation

No auto-confirm path exists. Every finding requires a human click before it is
final, and the database records who confirmed and when.

---

## 6. Data model

The unit of work is a package, not a document.

```
QualificationPackage
  coupon_no        WQT-139
  welder_id        TPL/GHAVP/W-72
  welder_name
  project, client, contractor
  wps_no
  status           incomplete | processing | review | complete
  documents        [SourceDocument]
  findings         [Finding]

SourceDocument
  doc_type         requisition | weld_data_record | sample_card |
                   lab_report | wpqr | id_card
  format_no        NPCIL/QMD/TF-127
  format_rev       R0
  template_matched bool
  page_count, sha256
  fields           [ExtractedField]

ExtractedField
  name, value, unit
  page, bbox                      <- region coordinates, for UI highlighting
  confidence
  read_method      template_region | full_page | checkbox_cv |
                   checkbox_vision | checkbox_agreed
  source_snippet

Finding
  finding_type     reconciliation | code_compliance | derivation_mismatch |
                   completeness
  severity         CRITICAL | MAJOR | MINOR
  field_name
  observed, expected
  clause_ref       QW-452.1(b)
  documents_involved [doc ids]
  status           open | confirmed | dismissed
  confirmed_by, confirmed_at
```

Every stored verdict carries `prompt_version`, `model_version`, `kb_version` and
`template_version`. A finding that cannot be traced to a specific reviewed rule
row and a specific region of a specific page is not a finding.

---

## 7. What already exists — reuse, do not rewrite

`backend/` is the Python source root; imports are `from engines.pdf_parser import
...`. `config.py` is the only module that touches the environment.

| Module | Lines | Status |
|---|---|---|
| `engines/pdf_parser.py` | 318 | Reuse. Add rotation detection, 300 DPI rasterisation, region cropping |
| `engines/llm_client.py` | 292 | Reuse the interface. Add image input to the signature |
| `utils/prompts.py` | — | Reuse. Versioned, append-only, never edit a prompt that has run |
| `engines/compliance_checker.py` | 411 | Reuse the shape and the unit handling. The rules it applies change |
| `knowledge_base/standards_loader.py` | 317 | Reuse the alias-and-parser pattern for P-numbers and F-numbers |
| `engines/doc_auditor.py` | 216 | Becomes a package orchestrator |
| `tests/` | 127 tests | All must keep passing |

The MTC path stays working. This is an addition, not a replacement.

---

## 8. Stack

**Keep:** Python 3.11 (pinned deps predate 3.13 wheels), FastAPI 0.111, uvicorn,
Pydantic 2.7.1 + pydantic-settings, PyMuPDF 1.24.5, pdfplumber 0.11.1, pytest.

**Add:** OpenCV (deskew, orientation, region cropping, checkbox ink density,
stamp and signature presence), a vision-capable LLM behind the existing
`LLMClient` interface.

**Remove:** `chromadb`, `langchain`.

**Demote:** Tesseract to orientation detection only.

**Later:** Supabase or Postgres with RLS, React 18 + Vite + TypeScript + Tailwind
+ React Query, Chrome MV3.

Put all data access behind a repository layer. NPCIL and defence sites are
air-gapped, and swapping hosted Postgres for self-hosted must be configuration,
not a rewrite.

---

## 9. Practices this problem demands

**Rule tables are reviewed data.** Every QW table entry carries `verified_by` and
`verified_date`. `kb_version` is stamped on every verdict. Unverified entries are
usable in development and must be visibly flagged in any output.

**Golden package regression suite.** Real packages with hand-written expected
findings, run on every commit. This catches a prompt change breaking thickness
derivation before a customer does. It matters more than raw test count.

**Determinism harness.** Cache extraction on `(page_hash, prompt_version,
model_version, template_version)`. The same package audited twice must produce
byte-identical findings — write a test asserting it. Vision models drift even at
temperature 0, and a QA tool that gives two answers to one document is finished.

**Bounding boxes as provenance.** Already tracking page and snippet; add region
coordinates so the UI can highlight the exact box a finding came from.

**Python conventions:** type hints throughout, Pydantic for every schema, async
endpoints, no business logic in route handlers, all model calls through
`LLMClient`, all prompts in `utils/prompts.py`.

**Commits:** `feat:` `fix:` `chore:` `test:` `docs:`

---

## 10. Data handling — non-negotiable

The sample documents contain welder photographs, full names, ID numbers and
signatures from an operating nuclear site. This is personal data in a way MTCs
were not.

- Real documents live in `fixtures/`, gitignored **from the first commit, before
  anything is copied in**
- Never commit a real document, a crop of one, or a photograph
- Never send document content to Sentry or any external logger
- The ASME Section IX PDF is copyrighted. Read it to build rule tables; never
  commit it, never store its text in the repo. Only extracted numeric and
  categorical rules enter the codebase — the same licensing position already
  taken with the ASTM thresholds
- Uploaded documents are deleted after extraction; only structured values are
  retained
- Test PDFs for unit tests are generated in-process with PyMuPDF

---

## 11. Build order

**1. Form classifier + template registry + region extraction.**
Prove it on the six sample documents. Foundation for everything else, and
testable immediately.

**2. Checkbox detector.**
Dual-read, CV and vision. Disagreement forces REVIEW.

**3. Package assembler.**
Group documents by coupon number and welder. Detect what is missing.

**4. Reconciliation engine.**
Cross-document field matching, date ordering. No code knowledge needed. The
WQT-139 name discrepancy is the first test case. **This demos to a site QA
manager before any rule table is written** — which is why it comes before
derivation.

**5. Section IX rule tables.**
QW-423 (P-numbers), QW-433 (F-numbers), QW-451/452 (thickness and test type),
QW-461.9 (position), QW-402.4 (backing), QW-405.3 (progression). Reviewer-marked.

**6. Derivation engine.**
Compute the qualified range from actual values, compare against the filled WPQR.

**7. Persistence.**
Schema informed by what the engines actually produce, not guessed in advance.

**8. API, then UI.**

---

## 12. Two features a site manager will ask for

Not V1, but they shape the schema — keep them buildable.

**Continuity tracking (QW-322).** Qualification lapses after six months without
using the process. Nobody tracks this properly today. It is pure date arithmetic
over data already held, and it produces "these 14 welders lapse in 30 days".

**Joint-to-welder lookup.** A supervisor has a 5F fillet on 72mm OD, 6mm thick
pipe. Which welders on site are qualified for it? Today that means hunting
through ID cards. With qualified ranges in a database it is one query. This is
what makes the tool live on site rather than in the QA office.

---

## 13. Open questions

1. **Is the WQT-139 welder name discrepancy real, or an OCR misread?** Verify
   against the original before using it as a test expectation.
2. **Which vision model does NVIDIA NIM actually serve?** Check before writing
   the client. The interface is provider-agnostic by design.
3. **Cloud or on-premise first?** Tier 1 (inspection agencies) tolerates cloud.
   NPCIL does not. Repository layer keeps the option open; the decision can wait.
4. **Accreditation friction.** Inspection agencies operate under ISO/IEC
   17020/17025. Adding a tool to an accredited process may require QMS
   validation, which undercuts the "zero workflow change" pitch. Unvalidated —
   ask one QA manager directly.

---

## 14. Commands

```bash
cd backend
py -3.11 -m venv venv
venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
cp .env.example .env

venv/Scripts/python.exe -m pytest tests/ -q                  # 127 tests
venv/Scripts/python.exe -m scripts.audit_cli --demo          # offline MTC verdicts
venv/Scripts/python.exe -m uvicorn api.main:app --reload --port 8000
```

---

## 15. Task handoff format

On completing a task, output:

```
DONE:           what was built
FILES CHANGED:  list
TESTS:          added / passing count
NEXT:           per the build order in section 11
BLOCKERS:       anything unresolved
ASSUMPTIONS:    anything decided without confirmation — label these explicitly
```

Never silently assume. If something is not in this document, ask.
