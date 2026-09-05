# Domain — Welder Qualification Packages

## The package

Six documents, one welder, one coupon number (`WQT-138`, `WQT-139`, ...).
Source: NPCIL GHAVP-1&2, Tata Projects as contractor.

```
Welder Qualification Requisition Sheet   NPCIL/QMD/TF/216
  who needs qualifying, process, electrode, position, P-numbers,
  pipe size / thickness, joint design
        |
        v
Weld Data Record                         NPCIL/QMD/TF-114(R0)   [landscape]
  actual parameters per pass: process, direction, filler type and size,
  travel speed, polarity, current min/max, voltage min/max, interpass temp,
  heat no, batch no, stringer/weave, visual exam result
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

## The critical structural fact

The WPQR has two columns. **Actual Values** are transcribed from the three raw
documents. **Qualified Range** is not copied from anywhere — it is *derived* by
applying Section IX rules to the actual values.

That derivation is the job. It is where errors hide, because a wrong qualified
range looks exactly like a right one on paper and only surfaces when a welder
works outside their actual qualification.

## Naming

`WQT-138` / `WQT-139` are **coupon numbers**, not code references.
`QW-350` is the welding variables clause. `QW-484` is the WPQR form.
`QW-301` is the qualification requirement. Do not conflate these.

---

## Check class 1 — Cross-document reconciliation

Pure string and value matching. No code knowledge required. Build this first.

- Welder name identical across all six documents
- Coupon number (WQT-xxx) consistent
- WPS number consistent
- Position, process, electrode consistent
- Base metal spec consistent
- Thickness consistent
- Date ordering: requisition <= weld <= sampling <= testing <= WPQR <= ID card
- Lab report number cited on the WPQR matches the actual lab report
- Every referenced document is present in the package

### First test case — a real finding in the sample set

The Weld Data Record dated 18.03.2026 is labelled coupon `WQT-139` but names
welder `AMIR CHAND CHAUDHARY`.

Every other WQT-139 document names `Raj Narayan Prasad`: the WPQR (WQT-139, exam
18.03.2026), the sample card (18.03.2026), and Star Wire report 140272. Amir
Chand belongs to WQT-138, tested 28.02.2026.

**Unverified.** This is either a real transcription error on a nuclear QA package
or an OCR misread. Confirm against the original before using it as a test
expectation. Either way it is exactly the class of finding the product exists to
catch.

## Check class 2 — Section IX rule compliance

Deterministic table lookup against encoded QW clauses.

- Test type matches coupon thickness (QW-452.1: 16mm plate -> 2 side bends)
- Bend acceptance criterion correct (QW-163)
- Required signatures and witness records present
- The testing lab is the one named on the sample card

## Check class 3 — Qualified range derivation

Compute the range from actual values, compare against what was filled in.
See `docs/rules-section-ix.md` for the tables.

---

## Two features a site manager will ask for

Not V1, but they shape the schema — keep them buildable.

**Continuity tracking (QW-322).** Qualification lapses after six months without
using the process. Nobody tracks this properly today. Pure date arithmetic over
data already held. Produces "these 14 welders lapse in 30 days".

**Joint-to-welder lookup.** A supervisor has a 5F fillet on 72mm OD, 6mm thick
pipe. Which welders on site are qualified for it? Today that means hunting
through ID cards. With qualified ranges in a database it is one query. This is
what makes the tool live on site rather than in the QA office.
