# Existing Code — Reuse, Do Not Rewrite

`backend/` is the Python source root. Imports are `from engines.pdf_parser import
...`, matching how uvicorn launches. `config.py` is the only module that reads
the environment; nothing else calls `os.environ` and no secret is hardcoded.

Scale: ~2,800 lines of source, ~1,000 lines of tests, 127 tests passing in ~3
seconds with no credentials and no network.

| Module | Lines | What to do with it |
|---|---|---|
| `engines/pdf_parser.py` | 318 | Reuse. Add rotation detection, 300 DPI rasterisation, region cropping |
| `engines/llm_client.py` | 292 | Reuse the interface. Add image input to the signature |
| `utils/prompts.py` | — | Reuse. Versioned, append-only |
| `engines/compliance_checker.py` | 411 | Reuse the shape and unit handling. The rules it applies change |
| `knowledge_base/standards_loader.py` | 317 | Reuse the alias-and-parser pattern for P-numbers and F-numbers |
| `engines/doc_auditor.py` | 216 | Becomes a package orchestrator |
| `utils/units.py` | — | Reuse as-is |
| `tests/` | 127 tests | All must keep passing |

## The MTC path stays working

This is an addition, not a replacement. `scripts/audit_cli.py --demo` runs seven
MTC scenarios offline and must keep passing.

## Patterns worth carrying over

**`LLMClient` as an abstract interface.** Nothing outside that module talks to a
provider. `MockLLMClient` returns canned responses so the whole pipeline is
testable offline, free and deterministically. Every downstream test uses it.

**Qualified requirement blocks.** The standards loader does not hold flat
`{grade: {property: {min, max}}}`. It holds several requirement blocks per grade
and selects the one matching product form and thickness. A grade whose limits
vary by thickness, presented without a thickness, raises `ThicknessRequiredError`
rather than picking a band. The same discipline applies to QW tables.

**No fuzzy matching on the lookup path.** `ASME SA-516 Gr.70`, `A516GR70`,
`sa516gr70` all resolve through an explicit alias table. Anything unrecognised
fails loudly.

**Recoverable failures become warnings, not exceptions.** A missing Tesseract
binary, an unOCRable page, a malformed table — all warnings on the returned
object. Only an unopenable file raises.

**Document problems vs infrastructure problems.** An unreadable scan, an
unparseable response, an unknown grade all return REVIEW carrying the reason,
because that *is* the answer. A provider outage raises `AuditError`, because it
says nothing about the document and retrying later is correct.

## Known gaps in what exists

- No LLM call has ever been made. Extraction accuracy is unknown.
- The OCR path has never run (Tesseract not installed).
- Table extraction has only seen synthetic text-only PDFs.
- All 10 MTC knowledge base grades are unverified against code books.
- Nothing is persisted anywhere.
