# CLAUDE.md — Complyx

Repo: `github.com/nishantgawderya1/complyx`
Commits: `nishantgawderya1 <nishantgawderya@gmail.com>`

## What this is

Complyx audits industrial QA documents against codes. **Current focus: ASME
Section IX welder performance qualification.** A welder qualification is a
package of six documents that must agree with each other and with the code.

An earlier MTC (Material Test Certificate) engine is built and passing 127 tests
offline. It stays working. This is an addition, not a replacement.

## The one rule

**AI extracts values. Deterministic code decides everything else.**

The vision model reads what is printed or marked on a form. It never derives a
qualified range, never compares a value to a rule, never emits a verdict.

### Never guess quietly

Any layer that cannot do its job confidently routes to REVIEW. Missing field,
unreadable form number, checkbox readers disagreeing, value with no unit, missing
document, rule not found in the tables — all REVIEW. A silent partial result that
looks complete is a defect, not a degraded mode.

No auto-confirm path exists. Every finding needs a human click, recorded with who
and when.

## Non-negotiables

- Real site documents live in `fixtures/`, gitignored **before** anything is
  copied in. They contain welder photos, names and ID numbers from a nuclear
  site.
- The ASME Section IX PDF is copyrighted. Read it to build rule tables. Never
  commit it, never store its text. Only extracted numeric and categorical rules
  enter the repo.
- No vector search on the verdict path. QW tables are discrete lookups.
  `chromadb` and `langchain` are unused — remove them from `requirements.txt`.
- Document content never goes to Sentry or any external logger.

## Stack

Python 3.11, FastAPI, Pydantic, PyMuPDF, pdfplumber, pytest, OpenCV, a
vision-capable LLM behind the existing `LLMClient` interface. `backend/` is the
source root (`from engines.pdf_parser import ...`). `config.py` is the only
module that touches the environment.

## Build order

1. Form classifier + template registry + region extraction
2. Checkbox detector (dual-read, CV + vision)
3. Package assembler
4. Reconciliation engine
5. Section IX rule tables
6. Derivation engine
7. Persistence
8. API, then UI

Reconciliation before derivation — it demos to a QA manager before any rule table
is written.

## Reference docs — read when the task needs them

| File | Read it when |
|---|---|
| `docs/domain.md` | Working on any of the six document types, or the check classes |
| `docs/architecture.md` | Touching extraction, templates, checkboxes, or the LLM client |
| `docs/data-model.md` | Touching schemas, persistence, or findings |
| `docs/rules-section-ix.md` | Building or using the QW rule tables |
| `docs/existing-code.md` | Reusing or modifying the MTC engine |
| `docs/practices.md` | Adding tests, prompts, or anything touching determinism |

Read only what the current task needs. Do not load all of them.

## Conventions

Type hints throughout. Pydantic for every schema. Async endpoints. No business
logic in route handlers. All model calls through `LLMClient`. All prompts in
`utils/prompts.py`, versioned and append-only — never edit a prompt that has run.

Commits: `feat:` `fix:` `chore:` `test:` `docs:`

## Commands

```bash
cd backend
venv/Scripts/python.exe -m pytest tests/ -q
venv/Scripts/python.exe -m scripts.audit_cli --demo
venv/Scripts/python.exe -m uvicorn api.main:app --reload --port 8000
```

## Handoff format

```
DONE:           what was built
FILES CHANGED:  list
TESTS:          added / passing count
NEXT:           per the build order above
BLOCKERS:       anything unresolved
ASSUMPTIONS:    anything decided without confirmation
```

Never silently assume. If something is not in these docs, ask.
