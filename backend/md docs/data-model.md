# Data Model

The unit of work is a **package**, not a document. This is the change from the
MTC engine, where one certificate was one audit.

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

## Provenance

Every stored verdict carries `prompt_version`, `model_version`, `kb_version` and
`template_version`.

A finding that cannot be traced to a specific reviewed rule row and a specific
region of a specific page is not a finding.

## Persistence notes

- Row Level Security on every table, all queries org-scoped
- `jobs` table for durable background work (see `docs/architecture.md`)
- Uploaded documents deleted after extraction; only structured values retained
- Schema gets written at build step 7, after the engines exist — informed by what
  they actually produce rather than guessed in advance
