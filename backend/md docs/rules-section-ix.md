# ASME Section IX — Rule Tables

**Status: none of these are reviewer-verified.** They were read off a single
sample WPQR (SMAW, plate, 3G, E7018, P1-to-P1). Treat every entry as
provisional until a qualified reviewer signs it.

The ASME Section IX PDF is copyrighted. Read it to build these tables. Never
commit it, never store its text. Only numeric and categorical rules enter the
repo — the same licensing position already taken with the ASTM thresholds.

## Derivation rules visible in the sample WPQR

| Actual value | Derived qualified range | Clause |
|---|---|---|
| P1 to P1 | P1 through P15F | QW-423.1 |
| F-No. 4 (E7018) | F4 with & without backing; F3, F2, F1 with backing | QW-433 |
| 16mm plate, 3+ layers checked | Max. to be welded | QW-452.1(b) |
| 3G groove, plate | Plate & pipe over 610mm OD, F & V; pipe 73-610mm OD, F; fillet F,H,V | QW-461.9 |
| Welded without backing | Qualifies with & without backing | QW-402.4 |
| Uphill progression | Uphill only | QW-405.3 |

## Tables to encode

| Table | Maps |
|---|---|
| QW-423 | Base metal spec -> P-number |
| QW-433 | Electrode classification -> F-number, and F-number substitution rules |
| QW-451 / QW-452 | Coupon thickness -> qualified thickness range, and required test type/count |
| QW-461.9 | Test position -> qualified positions, for groove and fillet, plate and pipe |
| QW-402.4 | Backing during test -> backing qualification |
| QW-405.3 | Vertical progression |
| QW-163 | Bend test acceptance criterion |
| QW-322 | Continuity / expiry (six months) |

## Encoding pattern

Same shape as the existing `astm_asme.json`: qualified lookup, alias table, no
fuzzy matching. Reuse the alias-and-parser approach from
`knowledge_base/standards_loader.py` for P-numbers and F-numbers — `E7018`,
`E-7018` and `SFA 5.1 E7018` must all resolve to one entry.

Each rule entry carries:

```
verified_by
verified_date
clause_ref        QW-452.1(b)
```

`kb_version` is stamped on every verdict. Unverified entries are usable in
development and must be **visibly flagged** in any output — never silently
treated as authoritative.

## Lookup discipline

No fuzzy matching on the verdict path. A rule not found returns "rule not found"
and routes to REVIEW. It never returns a near match. Returning the wrong row's
limits lets the arithmetic run perfectly and produces a confident wrong verdict
with no visible symptom.
