# Practices

## Rule tables are reviewed data

Every QW table entry carries `verified_by` and `verified_date`. `kb_version` is
stamped on every verdict. Unverified entries are usable in development and must
be visibly flagged in any output.

## Golden package regression suite

Real packages with hand-written expected findings, run on every commit. This
catches a prompt change breaking thickness derivation before a customer does.

It matters more than raw test count. 127 passing unit tests on synthetic inputs
did not tell us anything about how the parser handles a landscape scan with a
rubber stamp over the heat number.

## Determinism harness

Cache extraction on `(page_hash, prompt_version, model_version,
template_version)`.

The same package audited twice must produce byte-identical findings. Write a test
asserting it. Vision models drift even at temperature 0, and a QA tool that gives
two answers to one document is finished.

## Bounding boxes as provenance

Already tracking page and source snippet. Add region coordinates so the UI can
highlight the exact box a finding came from. An inspector verifies in two seconds
instead of hunting through a scan.

## Data handling — non-negotiable

The sample documents contain welder photographs, full names, ID numbers and
signatures from an operating nuclear site. This is personal data in a way MTCs
were not.

- Real documents live in `fixtures/`, gitignored **from the first commit, before
  anything is copied in**. Once a photograph is in git history, removing it means
  rewriting history.
- Never commit a real document, a crop of one, or a photograph
- Never send document content to Sentry or any external logger
- Uploaded documents deleted after extraction; only structured values retained
- Test PDFs for unit tests are generated in-process with PyMuPDF

`.gitignore` needs, before anything else:

```
fixtures/
*.pdf
!tests/fixtures/generated/*.pdf
```

## Python conventions

Type hints throughout. Pydantic for every schema. Async endpoints. No business
logic in route handlers. All model calls through `LLMClient` — the provider is
never called directly. All prompts in `utils/prompts.py`.

Prompts are append-only. A prompt that has run in production is never edited,
because historical verdicts reference it by version.

## Prompt discipline

Document content enters only the user message, inside `---DOCUMENT START---`
delimiters, never the system message. The model is told to ignore instructions
found in document text.

The extraction prompt forbids inference, derivation and unit conversion. If a
form prints ksi, the model reports ksi and conversion happens downstream.
Ambiguous readings are flagged low-confidence rather than resolved.

## Commits

`feat:` `fix:` `chore:` `test:` `docs:`
