# Complyx

Automated compliance verification for critical assets.

Complyx audits industrial engineering documents — Material Test Certificates,
welding procedure specifications, calibration records — against international
codes (ASME, ASTM, ISO, API). A QA engineer reviewing an MTC by hand spends
15–20 minutes cross-referencing printed values against a code book. Complyx
does the clerical half of that in seconds and hands the engineer a
parameter-by-parameter verdict with the governing clause attached.

It does not replace the inspector. It removes the transcription and lookup so
the inspector spends their time on engineering judgment.

---

## The one architectural rule

**AI extracts values. Deterministic code decides pass or fail.**

The LLM reads the certificate and reports what is printed on it. It never
compares a value to a threshold, and it never emits a verdict. Comparison is
plain Python arithmetic against a curated threshold table.

This is not stylistic. A wrong FAIL costs an inspector five minutes. A wrong
PASS lets non-conforming material into a pressure vessel, and it is the one
failure mode that ends the product. Arithmetic cannot hallucinate; a language
model can, so it is kept out of the decision entirely.

The same reasoning drives a second rule: **the system never guesses quietly.**
Every layer that cannot do its job with confidence says so, and the job routes
to `REVIEW_REQUIRED` for a human. A silent partial result that looks complete
is treated as a defect, not a degraded mode.

---

## Pipeline

```
PDF upload
   │
   ├─ pdf_parser        PyMuPDF native text · pdfplumber tables · Tesseract OCR
   │                    → page-attributed text + quality warnings
   │
   ├─ llm_client        Nemotron via NVIDIA NIM, versioned prompt
   │                    → structured values, each with page + source snippet
   │
   ├─ standards KB      threshold lookup for the identified grade
   │                    → min/max per property
   │
   ├─ compliance_checker   pure Python comparison
   │                    → PASS / FAIL / REVIEW per parameter, with delta
   │
   └─ human confirmation   mandatory. No auto-confirm path exists.
```

Every value carries provenance end to end: which page it came from, the
verbatim text it was read from, the prompt version that extracted it. An audit
result that cannot be traced back to a specific line of a specific page is not
an audit result.

---

## Build status

| Step | Component | State |
|---|---|---|
| 1 | `engines/pdf_parser.py` | Done, tested |
| 2 | `utils/prompts.py` | Done — needs real-MTC few-shots |
| 3 | `engines/llm_client.py` | Done — live model ID unconfirmed |
| 4 | `knowledge_base/standards_loader.py` | Done — 10 grades, all unverified |
| 5 | `engines/compliance_checker.py` | Done, tested |
| 6 | `engines/doc_auditor.py` | Done, tested |
| 7 | Pipeline validation on real MTCs | Blocked — no sample documents |

The pipeline runs end to end offline. 127 tests pass. To see it decide verdicts
without credentials or sample files:

```bash
python -m scripts.audit_cli --demo     # built-in scenarios
python -m scripts.audit_cli cert.pdf   # a real document
```

Backend AI pipeline first. No API layer, frontend or extension until step 7
passes on real documents.

---

## Layout

```
backend/
  api/            FastAPI app and routes
  engines/        parsing, LLM client, compliance logic, orchestration
  knowledge_base/ curated standards data + ChromaDB loader
  models/         Pydantic schemas
  utils/          versioned prompts, helpers
  tests/
  config.py       all environment access, via pydantic-settings
frontend/         React + Vite + TypeScript
extension/        Chrome MV3
```

`backend/` is the Python source root — imports are `from engines.pdf_parser
import …`, not `from backend.engines…`, matching how uvicorn is launched.

`config.py` is the only module that reads the environment. Nothing else calls
`os.environ`, and no secret is ever hardcoded.

---

## Setup

Requires **Python 3.11** — several pinned dependencies predate 3.13 wheels.

```bash
cd backend
py -3.11 -m venv venv
venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# source venv/bin/activate && pip install -r requirements.txt  # Unix

cp .env.example .env      # then fill in NVIDIA and Supabase keys
```

**Tesseract** is a system binary, not a pip package. Install it separately (on
Windows, the UB Mannheim build) and either put it on `PATH` or set
`TESSERACT_CMD` in `.env`. Without it, scanned certificates parse to an empty
result with a warning rather than failing — but they will not be readable.

```bash
uvicorn api.main:app --reload --port 8000   # from backend/
pytest tests/ -q
```

API docs at `http://localhost:8000/docs`.

---

## Components

### `engines/pdf_parser.py`

Produces one page-attributed text representation from an uploaded document.

Native text via PyMuPDF handles machine-generated supplier PDFs. Tables are
extracted separately with pdfplumber and rendered back into the text stream —
MTC values live in tables, and a flat text dump loses the row/column
association between a property name and its number. Pages yielding under 50
characters of native text are treated as scans and sent to Tesseract at 300 DPI.

Scans below 150 DPI are flagged: under that, digit strokes degrade and a 3 can
read as an 8. The document is marked low-quality rather than silently parsed.

Recoverable failures — missing Tesseract binary, a page that will not OCR, a
malformed table — become warnings on the returned `ParsedDocument`, not
exceptions. Only an unopenable file raises.

`ParsedDocument.has_text` is derived from per-page character counts, not from
`full_text`, because `full_text` always contains the `=== PAGE n ===` markers.
Testing the assembled string would report a blank scan as having content.

### `knowledge_base/standards_loader.py`

Resolves a material grade to its acceptance limits, deterministically.

Limits are **qualified**, not flat. The same grade has different carbon maxima
at different thicknesses and different strength minima at different diameters,
so a `StandardEntry` holds several requirement blocks and the loader selects the
one matching the certificate's product form and thickness. A grade whose limits
vary by thickness, presented without a thickness, returns an error rather than a
guessed band.

Lookup is an alias table plus a spec/grade parser — `ASME SA-516 Gr.70`,
`A516GR70` and `ASTM A516/A516M-17 Grade 70` all resolve to one entry. There is
no fuzzy matching on this path: returning Grade 60 limits for a Grade 70
certificate would let the arithmetic run perfectly and produce a confident wrong
PASS.

Every entry carries `source` and `verified`. All ten ship as `verified: false`
until a qualified reviewer checks them, and that flag is surfaced on every
verdict.

### `engines/compliance_checker.py`

Pure Python. Converts units, applies bounds, reports a delta and a clause per
parameter. One FAIL fails the document; anything unresolved forces REVIEW.

The interesting case is elongation, where codes set different minima for
different gauge lengths and certificates do not always say which was measured.
Rather than guess, the comparison brackets it: below every defined minimum is a
FAIL, at or above every minimum is a PASS, and in between is a REVIEW — a
verdict that cannot be wrong because of an unstated gauge length.

Unreported chemistry is treated by what the code asks. An element with a
specified minimum that is missing goes to review; a residual with only a maximum
is recorded as not checked, because mills routinely omit those and flagging them
would bury real findings.

### `engines/doc_auditor.py`

Orchestrates parse → extract → resolve → compare.

Document problems and infrastructure problems are handled differently. An
unreadable scan, an unparseable model response, an unknown grade or a missing
thickness all return a REVIEW verdict carrying the reason, because that is the
answer. A provider outage raises, because it says nothing about the certificate.

A document that yields no text never reaches the model — no tokens are spent on
a file that cannot be read.

### `utils/prompts.py`

Every prompt in the system, addressed by version. Nothing is inlined at a call
site, and the version is recorded with each call so any stored result can be
traced to the instructions that produced it. Versions are append-only — a
prompt that has run in production is never edited, because historical audits
reference it.

The extraction prompt forbids inference, derivation and unit conversion; if a
certificate prints ksi, the model reports ksi and conversion happens
downstream. Ambiguous readings are flagged with low confidence rather than
resolved. Document text enters only the user message, inside delimiters, never
the system message.

---

## Conventions

Python: type hints throughout, Pydantic for all schemas, async endpoints, no
business logic in route handlers. All LLM calls go through `LLMClient`; the
model is never called directly, so it stays swappable.

TypeScript: strict, no `any`. React Query for server state, `useState` for
local. No Redux.

Commits: `feat:` `fix:` `chore:` `test:`.

Data handling: uploaded PDFs are deleted after extraction; only structured
values are retained. Document content is never sent to Sentry or any external
logger. Row Level Security is enabled on every table and all queries are
org-scoped.

Real client documents never enter this repository. Test PDFs are generated
in-process.
