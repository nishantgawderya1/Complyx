# Complyx — Project Reference

**Automated compliance verification for critical assets.**

Repository: `github.com/nishantgawderya1/complyx`
Status: Phase 1 complete — backend AI pipeline runs end to end, offline.
Last updated: 17 August 2026

---

## 1. What Complyx is

Complyx audits industrial engineering documents against international codes.

Every manufactured component in heavy industry — a pressure vessel, a structural
weld, a piping run — ships with a document package: Material Test Certificates,
weld procedure qualifications, calibration records. Each must be verified
against the applicable code before sign-off.

Today a QA engineer does this by hand: open the MTC, read each printed value,
open the code book, find the material grade, compare every number, sign off or
raise a non-conformance. Fifteen to twenty-five minutes per document, three
hundred to a thousand documents on a mid-size project. That is 75–400 hours of
senior engineer time per project spent on clerical comparison, with a real miss
rate under fatigue.

Complyx does the clerical half in seconds and returns a parameter-by-parameter
verdict with the governing clause attached.

**It does not replace the inspector.** It removes the transcription and lookup so
the inspector spends their time on engineering judgment. Every result requires a
human confirmation before it is final.

### Who it is for

| Priority | User | Why them |
|---|---|---|
| Primary | QA/QC engineer at a third-party inspection agency (TÜV, Bureau Veritas, Intertek, DNV) | Bills by inspector-hour, so speed converts directly to margin. Highest document volume. |
| Secondary | QA head at an EPC contractor (L&T, Tata Projects, KEC) | Document review bottlenecks delay project closeout and trigger penalty clauses. |
| Tertiary | Plant QA manager at a manufacturer or utility (BHEL, NTPC, JSW) | Longer sales cycle, higher contract value, more regulatory constraint. |

### Value proposition

Time-to-clearance per document drops from ~20 minutes to under a minute. Every
audit is timestamped and traceable. The verdict cites the exact clause it came
from.

---

## 2. The one architectural rule

**AI extracts values. Deterministic code decides pass or fail.**

The LLM reads the certificate and reports what is printed on it. It never
compares a value to a threshold and never emits a verdict. Comparison is plain
Python arithmetic against a curated threshold table.

This is not stylistic. A wrong FAIL costs an inspector five minutes. A wrong PASS
lets non-conforming material into a pressure vessel, and it is the single failure
mode that ends the product. Arithmetic cannot hallucinate; a language model can,
so it is kept out of the decision entirely.

### The corollary: never guess quietly

Every layer that cannot do its job with confidence says so, and the document
routes to `REVIEW` for a human. A silent partial result that looks complete is
treated as a defect, not a degraded mode. Concretely:

- A missing value → REVIEW, not "nothing failed"
- A strength with no unit → REVIEW (480 is a pass in MPa and absurd in ksi)
- A thickness with no unit → REVIEW (12 mm and 12 in select different limits)
- A reading the model flagged as shaky → REVIEW, even if it would pass
- A poor-quality scan → can never return PASS, however clean the numbers look
- A grade not in the knowledge base → "standard not found", never a near match
- A document yielding no text → REVIEW, and no tokens are spent on it

---

## 3. Pipeline

```
PDF bytes
   |
   +-- pdf_parser         PyMuPDF native text - pdfplumber tables - Tesseract OCR
   |                      -> page-attributed text + quality warnings + SHA-256
   |
   +-- llm_client         versioned prompt -> provider -> validated JSON
   |                      -> values, each with page + verbatim source snippet
   |
   +-- standards_loader   grade + product form + thickness
   |                      -> the one requirement block governing this certificate
   |
   +-- compliance_checker pure Python arithmetic
   |                      -> PASS / FAIL / REVIEW per parameter, delta, clause
   |
   +-- human confirmation mandatory. No auto-confirm path exists.
```

Provenance runs end to end: which page a value came from, the verbatim text it
was read from, the prompt version that extracted it, the model that produced it,
and whether the thresholds applied were reviewer-verified. An audit result that
cannot be traced back to a specific line of a specific page is not an audit
result.

---

## 4. Tech stack

### In use today

| Layer | Technology | Version | Notes |
|---|---|---|---|
| Language | Python | 3.11.9 | Pinned deps predate 3.13 wheels |
| API framework | FastAPI | 0.111.0 | Health endpoint only so far |
| Server | uvicorn | 0.30.1 | |
| Validation / config | Pydantic + pydantic-settings | 2.7.1 / 2.3.4 | Strict schemas everywhere |
| PDF text | PyMuPDF (fitz) | 1.24.5 | Primary parser |
| PDF tables | pdfplumber | 0.11.1 | MTC values live in tables |
| OCR | pytesseract | 0.3.10 | **Tesseract binary not installed** |
| Imaging | Pillow | 10.3.0 | Page rasterisation for OCR |
| Tests | pytest | 8.2.2 | 127 passing |

### Declared but not yet installed

| Package | Purpose | Status |
|---|---|---|
| `openai` | NVIDIA NIM client (OpenAI-compatible) | Needed for the live LLM path |
| `supabase` | DB + auth + storage | Needed for Phase 2 |
| `slowapi` | Rate limiting | Phase 5 hardening |
| `sentry-sdk` | Error tracking | Phase 5 hardening |
| `chromadb`, `langchain` | Vector search over standards | **Currently unused** — see section 9 |

### Planned, not started

React 18 + Vite + TypeScript + Tailwind + React Query (frontend), Chrome MV3
(extension), Railway + Vercel + Supabase (infrastructure).

---

## 5. Repository layout

```
complyx/
├── README.md                  engineering documentation
├── PROJECT.md                 this file
├── .gitignore
├── backend/
│   ├── config.py              ALL environment access, via pydantic-settings
│   ├── requirements.txt
│   ├── .env.example
│   ├── api/
│   │   ├── main.py            FastAPI app — health endpoint only
│   │   └── routes/            empty; Phase 2
│   ├── engines/
│   │   ├── pdf_parser.py          318 lines
│   │   ├── llm_client.py          292 lines
│   │   ├── compliance_checker.py  411 lines
│   │   └── doc_auditor.py         216 lines
│   ├── knowledge_base/
│   │   ├── standards_loader.py    317 lines
│   │   └── standards_data/astm_asme.json
│   ├── models/                document, extraction, standards, audit
│   ├── utils/                 prompts.py, units.py
│   ├── scripts/audit_cli.py   runnable demo + real-file audit
│   └── tests/                 6 files, 127 tests
├── frontend/src/              EMPTY — nothing built
└── extension/src/             EMPTY — nothing built
```

`backend/` is the Python source root — imports are `from engines.pdf_parser
import ...`, matching how uvicorn is launched. `config.py` is the only module
that reads the environment; nothing else calls `os.environ` and no secret is ever
hardcoded.

**Scale:** 33 tracked files, ~2,800 lines of source, ~1,000 lines of tests,
13 commits.

---

## 6. What is built

### `engines/pdf_parser.py` — done, 9 tests

Produces one page-attributed text representation from an uploaded document.

Native text via PyMuPDF handles machine-generated supplier PDFs. Tables are
extracted separately with pdfplumber and rendered back into the text stream,
because MTC values live in tables and a flat text dump loses the row/column
association between a property name and its number. Pages yielding under 50
characters of native text are treated as scans and sent to Tesseract at 300 DPI.

Scans below 150 DPI are flagged — under that, digit strokes degrade and a 3 can
read as an 8. The document is marked low-quality rather than silently parsed.

Recoverable failures — missing Tesseract binary, a page that will not OCR, a
malformed table — become warnings on the returned `ParsedDocument`, not
exceptions. Only an unopenable file raises.

`ParsedDocument.has_text` is derived from per-page character counts, not from
`full_text`, because `full_text` always contains the `=== PAGE n ===` markers.
Testing the assembled string would report a blank scan as having content.

### `utils/prompts.py` — done, needs real few-shots

Every prompt in the system, addressed by version, registered in one file. Nothing
is inlined at a call site, and the version is recorded with each call so a stored
result traces back to the instructions that produced it. Versions are
append-only: a prompt that has run in production is never edited, because
historical audits reference it.

The extraction prompt forbids inference, derivation and unit conversion — if a
certificate prints ksi, the model reports ksi and conversion happens downstream.
Ambiguous readings are flagged with low confidence rather than resolved. Multiple
heat numbers are reported, never merged. Document text enters only the user
message, inside `---DOCUMENT START---` delimiters, never the system message, and
the model is told to ignore instructions found in document text.

**Gap:** carries one clearly-labelled synthetic example. Real few-shots from
actual supplier formats will move accuracy more than any other single change.

### `engines/llm_client.py` — done, 17 tests

`LLMClient` is an abstract interface. Nothing outside this module talks to a
provider, so the model is swappable by configuration rather than by editing
business logic — which matters because the configured Nemotron build is
unconfirmed.

Two implementations: `NvidiaLLMClient` (OpenAI-compatible endpoint, lazy import
so the mock path needs no provider package) and `MockLLMClient` (canned
responses, used by every downstream test — the whole pipeline is testable
offline, free and deterministically).

Model output is validated against the extraction schema before any caller sees
it. Responses wrapped in markdown fences or padded with prose are tolerated;
anything that will not validate is retried once and then fails as
REVIEW_REQUIRED rather than being partially trusted. Token counts, latency,
attempts and prompt version are recorded per call.

### `knowledge_base/standards_loader.py` — done, 35 tests

Resolves a material grade to its acceptance limits, deterministically.

Limits are **qualified**, not flat. The same grade has different carbon maxima at
different thicknesses and different strength minima at different diameters, so a
`StandardEntry` holds several requirement blocks and the loader selects the one
matching the certificate's product form and thickness. A grade whose limits vary
by thickness, presented without a thickness, raises `ThicknessRequiredError`
rather than picking a band.

Lookup is an alias table plus a spec/grade parser. `ASME SA-516 Gr.70`,
`A516GR70`, `sa516gr70` and `ASTM A516/A516M-17 Grade 70` all resolve to one
entry. There is deliberately **no fuzzy matching** on this path: returning Grade
60 limits for a Grade 70 certificate would let the arithmetic run perfectly and
produce a confident wrong PASS with no visible symptom.

### `engines/compliance_checker.py` — done, 28 tests

Pure Python. Converts units, applies bounds, reports a delta and a clause per
parameter. One FAIL fails the document; anything unresolved forces REVIEW; a
document where nothing could be checked is REVIEW, never PASS — "no findings"
and "no checks performed" are different statements.

Three domain decisions worth knowing:

**Elongation is bracketed, not guessed.** Codes set different minima for
different gauge lengths (17% over 200 mm, 21% over 50 mm for A516 Gr.70) and
certificates do not always say which was measured. Below every defined minimum is
a FAIL, at or above every minimum is a PASS, and in between is a REVIEW. An
unstated gauge length cannot produce a wrong verdict.

**Unreported chemistry is treated by what the code asks.** An element with a
specified minimum that is missing goes to review. A residual with only a maximum
is recorded as `NOT_CHECKED`, because mills routinely omit those and flagging
them would bury real findings.

**A value exactly at the limit passes.** A specified minimum is inclusive, and a
small epsilon keeps 484.99999 from failing a 485 minimum.

### `engines/doc_auditor.py` — done, 17 tests

Orchestrates parse → extract → resolve → compare.

Document problems and infrastructure problems are handled differently. An
unreadable scan, an unparseable model response, an unknown grade or a missing
thickness all return a REVIEW verdict carrying the reason, because that *is* the
answer. A provider outage raises `AuditError`, because it says nothing about the
certificate and retrying later is the right response.

### `scripts/audit_cli.py` — done

```bash
python -m scripts.audit_cli --demo      # seven built-in scenarios, offline
python -m scripts.audit_cli cert.pdf    # audit a real document
```

### `api/main.py` — boilerplate only

`GET /health`, `GET /`, plus generated `/docs` and `/openapi.json`. The health
endpoint doubles as a local-environment report — it says whether Tesseract is
reachable and whether the NVIDIA and Supabase credentials are present, never
their values. Missing credentials warn at startup rather than failing.

---

## 7. What works right now — verified

**127 tests pass** in ~3 seconds, with no credentials and no network.

| Test file | Tests | Covers |
|---|---|---|
| `test_compliance_checker.py` | 28 | Bounds, thresholds, elongation bracketing, chemistry, aggregation |
| `test_standards_loader.py` | 35 | Grade-string variants, band selection, near-miss confusion |
| `test_units.py` | 21 | Conversion factors, unknown-unit rejection |
| `test_llm_client.py` | 17 | Response parsing, schema rejection, retry, prompt isolation |
| `test_doc_auditor.py` | 17 | End-to-end with real parser/KB/engine, mocked model only |
| `test_pdf_parser.py` | 9 | Text, page attribution, hashing, blank-document flagging |

### The demo, end to end

`python -m scripts.audit_cli --demo` runs seven scenarios through the real
pipeline with only the model call mocked:

| Scenario | Verdict |
|---|---|
| Tensile 480 MPa against a 485 MPa minimum | **FAIL** — delta −5, clause cited |
| Fully conforming certificate | **PASS** |
| Imperial units (75 ksi, 0.5 in) | **PASS** — converted to 517 MPa |
| Grade not in knowledge base | **REVIEW** — no comparison attempted |
| Thickness missing on a thickness-banded grade | **REVIEW** |
| Model flagged a reading as uncertain | **REVIEW** |
| Strength value with no unit | **REVIEW** |

There is also a parametrised test asserting that **no degraded input can ever
produce PASS**.

---

## 8. What is NOT built, and what is unverified

### Not built at all

| Area | Status |
|---|---|
| API routes (auth, projects, audit submit/poll/result/confirm) | Phase 2 — not started |
| Supabase schema, RLS, persistence | Not started; no verdict is stored anywhere |
| Frontend (React) | Empty directory |
| Chrome extension | Empty directory |
| PDF report export | V1.1 |
| Non-conformance tracking / CAPA | V2 |
| NDT defect detection (YOLOv8) | V2 |
| Docker / docker-compose, deployment | Not started |

Nothing is persisted. The CLI prints a verdict and it is gone.

### Built but never exercised against reality

| Gap | Consequence |
|---|---|
| **No LLM call has ever been made** | Extraction accuracy is entirely unknown |
| **The OCR path has never run** | Tesseract is not installed; scanned certificates — the hard and most valuable case — are untested code |
| **Table extraction has never seen a real table** | Tests use synthetic text-only PDFs; pdfplumber behaviour on real MTC layouts is unknown |
| **All 10 knowledge base grades are unverified** | Values came from public summaries, not code books |
| **Dependency resolution untested** | `chromadb`/`langchain` against pydantic 2.7.1 may conflict on install |
| **The model ID is unconfirmed** | `nemotron-4-340b-instruct` is a mid-2024 model and may no longer be served |

---

## 9. Knowledge base detail

Ten grades, chosen to cover roughly 80% of Indian heavy-industry MTC review.

| Canonical key | Specification | Grade | Bands | Verified |
|---|---|---|---|---|
| `ASTM_A36` | ASTM A36/A36M | — | 3 | no |
| `ASTM_A516_60` | ASTM A516/A516M | 60 | 3 | no |
| `ASTM_A516_70` | ASTM A516/A516M | 70 | 4 | no |
| `ASTM_A106_B` | ASTM A106/A106M | B | 1 | no |
| `ASTM_A53_B` | ASTM A53/A53M | B | 1 | no |
| `ASTM_A312_TP304` | ASTM A312/A312M | TP304 | 1 | no |
| `ASTM_A312_TP316` | ASTM A312/A312M | TP316 | 1 | no |
| `ASME_SA240_TP304` | ASME SA-240/SA-240M | TP304 | 1 | no |
| `ASTM_A479_TP316` | ASTM A479/A479M | TP316 | 1 | no |
| `ASTM_A193_B7` | ASTM A193/A193M | B7 | 3 | no |

"Bands" are qualified requirement blocks. A516 Gr.70 has four thickness bands
whose carbon maxima differ (0.27 → 0.28 → 0.30 → 0.31). A193 B7 has three
diameter bands whose yield minima differ (720 → 655 → 515 MPa). A312 TP304 and
SA-240 TP304 are separate entries because their chromium ranges differ despite
both being "304".

### Licensing position

Only **numeric limits** are stored — factual data, not copyrightable expression.
No standard text is reproduced. This avoids the ASME/ASTM licensing exposure that
would come from embedding clause text, at the cost of requiring a reviewer to
confirm each number.

### Why ChromaDB is unused

`chromadb` and `langchain` remain in `requirements.txt` per the original spec but
nothing imports them. With a few dozen grades, an alias table plus a spec/grade
parser is both more accurate and fully auditable, and it has no silent failure
mode. Vector search on the path that decides verdicts can return the wrong
grade's limits with no visible symptom. **This is an open decision** — the
dependencies can be dropped, which would also remove the pydantic conflict risk.

---

## 10. Deviations from AGENT_CONTEXT.md

| Spec said | Built | Why |
|---|---|---|
| Flat `{grade: {property: {min, max}}}` | Qualified requirement blocks keyed on form + thickness + condition | Flat tables produce false FAILs on thickness-dependent grades; retrofitting means rewriting the KB and comparator together. Agreed with the user. |
| ChromaDB vector retrieval | Deterministic alias + parser lookup | Fuzzy match on the verdict path can silently apply the wrong grade's limits |
| `backend/config.py` not in the tree | Added | pydantic-settings needs a home; spec requires `settings.VARIABLE` |
| `models/` has `audit.py`, `project.py` | Added `document.py`, `extraction.py`, `standards.py` | Each engine's contract needs a schema |

Extraction also captures `product_form` and `nominal_thickness`, which the flat
spec did not need but the qualified model requires.

---

## 11. Roadmap

### V1 remaining

- **Step 7 — validate on real MTCs.** Blocked on sample documents.
- Real few-shot examples in the extraction prompt
- Document-type classifier (reject invoices and drawings gracefully)
- Phase 2: Supabase schema with RLS, auth middleware, project CRUD, audit routes
  with background processing and status polling, confirm endpoint
- Phase 3: React frontend — login, project list, upload, result view, dashboard
- Phase 4: Chrome MV3 extension
- Phase 5: Sentry, rate limiting, security audit, Railway + Vercel deploy

### V1.1 / V2

PDF report export, expanded knowledge base (25+ grades), multi-user roles,
non-conformance tracking and CAPA, email notifications, NDT defect detection.

### V3+

On-premise Docker, SCADA anomaly detection, AI-drafted NCR text, ERP API,
mobile app.

### Explicitly not building

EHS video monitoring, predictive maintenance, CAPA pattern mining, voice input,
multi-language, workflow approval chains, agent frameworks
(LangGraph/AutoGen/CrewAI), microservices.

---

## 12. What is needed to move forward

### Blocking

**1. Real MTC PDFs — 20 to 30.** The mix matters more than the count:

| Type | Count | Exercises |
|---|---|---|
| Clean machine-generated | ~10 | The baseline case |
| Scanned / photocopied with stamps | ~8 | OCR — currently untested |
| Imperial units (ksi, psi) | 2–3 | Unit conversion |
| Multi-page, values split across pages | 2–3 | Page attribution |

Across 3+ suppliers and 3+ grades from the V1 list. Redaction is fine — supplier
name, project, PO, price can all be blacked out. What must survive: grade,
specification, heat number, mechanical values, chemistry, units, product form,
thickness.

**2. NVIDIA NIM API key**, plus confirmation the model ID is still served:

```bash
curl -s https://integrate.api.nvidia.com/v1/models \
  -H "Authorization: Bearer $NVIDIA_API_KEY" | grep -i nemotron
```

**3. Threshold sources.** In order of usefulness: actual code tables (a photo or
PDF page of e.g. *ASTM A516 Table 2*) > producer/mill datasheets > research
papers. Each grade needs the numbers **plus** product form, thickness range,
heat-treat condition and units.

### Needed within days

**4. Supabase project** — URL, anon key, service role key. Blocks Phase 2.
**5. Tesseract installed** (UB Mannheim Windows build), then `TESSERACT_CMD` set.
**6. A `.env` file** — none exists yet.

### Before any real inspector sees a verdict

**7. A domain reviewer** — someone who actually reviews MTCs, to check the
threshold table and the extracted field list. A correctness gate on the product's
core claim, not a formality. Does not block development.

---

## 13. Setup and commands

Requires **Python 3.11** — several pinned dependencies predate 3.13 wheels.

```bash
cd backend
py -3.11 -m venv venv
venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
cp .env.example .env                                         # then fill in keys
```

**Tesseract** is a system binary, not a pip package. Install it separately and
either put it on `PATH` or set `TESSERACT_CMD` in `.env`. Without it, scanned
certificates parse to an empty result with a warning rather than failing — but
they will not be readable.

```bash
venv/Scripts/python.exe -m pytest tests/ -q          # 127 tests
venv/Scripts/python.exe -m scripts.audit_cli --demo  # offline verdicts
venv/Scripts/python.exe -m uvicorn api.main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs`, health at `/health`.

---

## 14. Risks and open questions

### Product risks

| Risk | Status |
|---|---|
| **Accreditation friction** — inspection agencies operate under ISO/IEC 17020/17025, so adding a tool to an accredited process may require QMS validation, undercutting the "zero workflow change" pitch | Unvalidated. Ask one QA manager directly. |
| **Data sensitivity** — clients may prohibit uploading supplier documents to a cloud SaaS | Unvalidated |
| **Extraction accuracy below ~90%** would mean more manual review, not less | Unknown until real documents are run |
| **Liability** on a wrong PASS | Mitigated architecturally (human confirmation, never-guess rules); not addressed legally |
| **Per-document pricing** makes customers ration usage, killing the habit | Per-seat pricing recommended, untested |

### Engineering open questions

1. Is `nemotron-4-340b-instruct` still served? It is also text-only, which
   matters if scanned certificates dominate — a vision model reading page images
   may beat OCR-then-text. The `LLMClient` interface currently takes a text blob;
   supporting page images would change that signature.
2. Drop `chromadb` and `langchain` from `requirements.txt`?
3. `.gitattributes` with `* text=auto eol=lf` — git warns on every file, and the
   Docker build (Linux) will disagree with the Windows checkout.
4. The audit trail needs `prompt_version`, `model_version` and `kb_version` per
   stored job. The verdict model carries them; the database schema does not yet.
5. The data model has no equipment-item level. Persona 2 describes "1,200
   equipment items, each with a full document package", and cross-document
   reconciliation (does the heat number on the MTC match the traceability
   record?) is where the real reviewer time goes. Single-document MTC checking is
   the demo; package reconciliation is the defensible product.

---

## 15. Conventions

**Python:** type hints throughout, Pydantic for all schemas, async endpoints, no
business logic in route handlers. All LLM calls go through `LLMClient`; the model
is never called directly. All prompts live in `utils/prompts.py`.

**Commits:** `feat:` `fix:` `chore:` `test:` `docs:`. Authored as
`nishantgawderya1 <nishantgawdiya@gmail.com>`.

**Data handling:** uploaded PDFs are deleted after extraction; only structured
values are retained. Document content is never sent to Sentry or any external
logger. Row Level Security on every table, all queries org-scoped.

**Real client documents never enter this repository.** Test PDFs are generated
in-process with PyMuPDF.
