# Architecture

Read this before proposing alternatives. These decisions have reasons.

## These are numbered forms, not free-form documents

Every document carries a format number and revision in its header
(`NPCIL/QMD/TF-127, Rev.R0`). The same six templates repeat across every welder
package on the site.

So do **not** do general document understanding. Classify the form, look up its
template, read only the known field regions.

```
page image
  -> deskew / orientation correction        (OpenCV + PyMuPDF)
  -> form classifier: read format no.       (cheap, header region only)
  -> template registry lookup               (TF-127-R0 -> field regions)
  -> crop each region, read that region     (vision model, small crops)
  -> field value + bounding box + confidence
```

Higher accuracy, roughly an order of magnitude lower cost, and every value
arrives with the coordinates it came from — which the UI later uses to highlight
the exact box a finding came from.

When the format number is unrecognised: fall back to whole-page vision
extraction, mark the document `template_unknown` so a human knows which path
produced the values. Never silently guess a template.

Note the Weld Data Record (TF-114) is **landscape**. Orientation detection runs
before anything else.

## Checkboxes get read twice

The "3 layers minimum: Yes/No" checkbox on the WPQR decides between "max. to be
welded" and a 2t thickness limit. It is the single most consequential mark on the
form and it is not text.

Read it two independent ways:

1. **OpenCV** — crop the box, threshold, measure ink density inside the rectangle
2. **Vision model** — crop the same region, ask checked or unchecked

Agreement -> high confidence. **Disagreement -> REVIEW, always.** Never resolve
the conflict automatically.

## A vision model is required

Text-only OCR cannot see checkbox state, cannot preserve the Actual Values vs
Qualified Range column association, and degrades badly on stamped and signed
scans. Tesseract stays only for coarse orientation detection.

`LLMClient` keeps its provider-agnostic interface. The signature changes to
accept page images alongside text.

**Confirm what NVIDIA NIM actually serves before committing to a model ID** —
`nemotron-4-340b-instruct` is text-only and dated. The interface exists precisely
so this is a config change, not a rewrite.

## No vector search on the verdict path

QW-423, QW-433, QW-451/452, QW-461.9 are **tables**: discrete inputs, discrete
outputs. Encode them as versioned rule data, same pattern as the existing
`astm_asme.json`.

Vector retrieval can return the wrong row with no visible symptom. That is the
exact failure mode the whole architecture is built to avoid — a confident wrong
answer with nothing to flag it.

`chromadb` and `langchain` are unused dead weight in `requirements.txt` and carry
a pydantic conflict risk. Remove them.

RAG belongs only on the **explanation layer** — showing an inspector the clause
text behind a finding, answering "why does 3G qualify pipe over 610mm OD". It
never decides anything. When that arrives, use `pgvector` in the existing
Postgres, not a separate service: one database, RLS already applies, nothing
extra to run on an air-gapped site.

## Background jobs must survive restarts

A six-document package is 20-40 page reads. Minutes, not seconds. FastAPI
`BackgroundTasks` lose work silently on restart, which is unacceptable for a
nuclear QA audit.

Do not reach for Celery or Redis. A `jobs` table in Postgres plus a worker loop
polling it survives restarts, is inspectable in plain SQL, and adds one process.

## Deployment optionality

Put all data access behind a repository layer. NPCIL and defence sites are
air-gapped. Swapping hosted Postgres for self-hosted must be configuration, not a
rewrite.

Tier 1 customers (third-party inspection agencies) tolerate cloud. That makes
cloud-first defensible for V1 — but only if the option stays open.

## Stack

**Keep:** Python 3.11 (pinned deps predate 3.13 wheels), FastAPI 0.111, uvicorn
0.30.1, Pydantic 2.7.1 + pydantic-settings, PyMuPDF 1.24.5, pdfplumber 0.11.1,
pytest 8.2.2.

**Add:** OpenCV (deskew, orientation, region cropping, checkbox ink density,
stamp and signature presence detection), a vision-capable LLM behind
`LLMClient`.

**Remove:** `chromadb`, `langchain`.

**Demote:** Tesseract to orientation detection only.

**Later:** Postgres with RLS, React 18 + Vite + TypeScript + Tailwind + React
Query, Chrome MV3.

PyMuPDF gains a bigger role: page rasterisation at 300 DPI, rotation detection,
region cropping.
