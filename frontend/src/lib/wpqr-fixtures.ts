/**
 * Development fixtures for WPQR generation.
 *
 * Modelled on the real NPCIL GHAVP-1&2 package: SMAW, 3G uphill, 16mm plate,
 * E7018, P1-to-P1, welded without backing, six passes. Welder names and ID
 * numbers are **invented** -- the real ones stay gitignored (CLAUDE.md s10).
 *
 * Two things here are worth reading rather than skimming, because they are the
 * argument for generating a WPQR rather than checking one:
 *
 * 1. `three_layers` is derived from the Weld Data Record's **pass count**, not
 *    read from a tickbox. The source document lists six passes, so three or
 *    more layers is a fact about the evidence. That is better provenance than
 *    the printed form has, where the same question is an ambiguous ink mark
 *    that two readers disagreed about.
 *
 * 2. `thickness_qualified` is blocked, not guessed. The lab report in this
 *    sample records two side bends, but QW-451.1 wants the coupon thickness
 *    confirmed against the bend count before the range can be stated. Missing
 *    input produces "cannot derive", never the common answer.
 */

import type { Evidence, UploadedFile, WpqrCell, WpqrDraft } from './types';

function ev(
  slot: Evidence['slot'],
  field_label: string,
  value: string,
  page: number,
  bbox: Evidence['bbox'],
  confidence = 0.94,
  read_method: Evidence['read_method'] = 'template_region',
): Evidence {
  return { slot, field_label, value, page, bbox, confidence, read_method };
}

export const SOURCES: UploadedFile[] = [
  {
    slot: 'requisition',
    filename: 'welder requisition sheet(10-08-2026).pdf',
    size_bytes: 215_239,
    state: 'matched',
    raw_format_text: 'Format No: NPCIL/QMD/TF/216',
    canonical_key: 'TF-216',
    confidence: 0.95,
    page_count: 1,
  },
  {
    slot: 'weld_data_record',
    filename: 'Welder Data Record.pdf',
    size_bytes: 863_152,
    state: 'matched',
    raw_format_text: 'Format No: NPCIL/OMD/TE. 114(R0)',
    canonical_key: 'TF-114-R0',
    confidence: 0.9,
    page_count: 2,
  },
  {
    slot: 'lab_report',
    filename: 'Lab Test Report.pdf',
    size_bytes: 703_915,
    state: 'matched',
    raw_format_text: 'SWILPL/7.8F/01',
    canonical_key: 'SWILPL-078F-01',
    confidence: 0.88,
    page_count: 2,
  },
];

const CELLS: WpqrCell[] = [
  /* ---------------- identification ---------------- */
  {
    id: 'welder_name',
    variable: "Welder's name",
    group: 'identification',
    actual: 'DEVENDRA SINGH',
    derived: null,
    clause_ref: null,
    evidence: [
      ev('requisition', "Welder's name", 'Devendra Singh', 1, {
        x0: 0.14, y0: 0.31, x1: 0.29, y1: 0.34,
      }),
      ev('weld_data_record', 'Welder name', 'DEVENDRA SINGH', 1, {
        x0: 0.18, y0: 0.148, x1: 0.42, y1: 0.172,
      }),
    ],
    state: 'confirmed',
    rule_verified: true,
    confirmed_by: 'RK',
    confirmed_at: '2026-09-13',
  },
  {
    id: 'welder_id',
    variable: 'Identification no.',
    group: 'identification',
    actual: 'TPL/GHAVP/W-72',
    derived: null,
    clause_ref: null,
    evidence: [
      ev('weld_data_record', 'Welder ID', 'TPL/GHAVP/W-72', 1, {
        x0: 0.18, y0: 0.175, x1: 0.36, y1: 0.198,
      }),
    ],
    state: 'derived',
    rule_verified: true,
  },
  {
    id: 'coupon_no',
    variable: 'Test coupon no.',
    group: 'identification',
    actual: 'WQT-139',
    derived: null,
    clause_ref: null,
    evidence: [
      ev('weld_data_record', 'Coupon no.', 'WQT-139', 1, {
        x0: 0.72, y0: 0.318, x1: 0.83, y1: 0.34,
      }),
      ev('lab_report', 'Sample ID', 'WQT-139', 1, {
        x0: 0.61, y0: 0.22, x1: 0.72, y1: 0.243,
      }, 0.91),
    ],
    state: 'derived',
    rule_verified: true,
  },
  {
    id: 'wps_no',
    variable: 'Identification of WPS followed',
    group: 'identification',
    actual: 'TPL/GHAVP1&2/SMAW/WPS-01 R-0',
    derived: null,
    clause_ref: null,
    evidence: [
      ev('requisition', 'WPS no.', 'TPL/GHAVP1&2/SMAW/WPS-01 R-0', 1, {
        x0: 0.4, y0: 0.31, x1: 0.62, y1: 0.34,
      }),
      ev('weld_data_record', 'WPS no.', 'TPL/GHAVP1&2/SMAW/WPS-01', 1, {
        x0: 0.6, y0: 0.34, x1: 0.84, y1: 0.363,
      }, 0.89),
    ],
    state: 'derived',
    rule_verified: true,
  },
  {
    id: 'date_welded',
    variable: 'Date welded',
    group: 'identification',
    actual: '18.03.2026',
    derived: null,
    clause_ref: null,
    evidence: [
      ev('weld_data_record', 'Date of test', '18.03.2026', 1, {
        x0: 0.18, y0: 0.2, x1: 0.29, y1: 0.222,
      }),
    ],
    state: 'derived',
    rule_verified: true,
  },

  /* ---------------- QW-350 welding variables ---------------- */
  {
    id: 'process',
    variable: 'Welding process',
    group: 'variables',
    actual: 'SMAW, manual',
    derived: 'SMAW, manual',
    clause_ref: 'QW-404',
    rule_note:
      'Process qualified is the process welded. No substitution is permitted.',
    evidence: [
      ev('requisition', 'Process', 'SMAW', 1, {
        x0: 0.11, y0: 0.36, x1: 0.19, y1: 0.383,
      }),
      ev('weld_data_record', 'Process (all passes)', 'SMAW ×6', 1, {
        x0: 0.2, y0: 0.42, x1: 0.3, y1: 0.62,
      }),
    ],
    state: 'derived',
    rule_verified: false,
  },
  {
    id: 'p_number',
    variable: 'Base metal P-number',
    group: 'variables',
    actual: 'P1 to P1',
    derived: 'P1 through P15F',
    clause_ref: 'QW-423.1',
    rule_note:
      'IS 2062 E250 Gr.BR maps to P-No. 1. A coupon welded P1 to P1 qualifies the welder for P1 through P15F.',
    evidence: [
      ev('weld_data_record', 'Material spec (both plates)', 'IS 2062 E250 Gr.BR', 1, {
        x0: 0.55, y0: 0.45, x1: 0.78, y1: 0.5,
      }),
      ev('requisition', 'M1 / M2 P-no.', 'P1 / P1', 1, {
        x0: 0.29, y0: 0.36, x1: 0.4, y1: 0.383,
      }),
    ],
    state: 'derived',
    rule_verified: false,
  },
  {
    id: 'f_number',
    variable: 'Filler metal F-number',
    group: 'variables',
    actual: 'F-No. 4 (SFA 5.1, E7018)',
    derived:
      'F-No. 4 with and without backing; F-No. 3, 2 and 1 with backing',
    clause_ref: 'QW-433',
    rule_note:
      'E7018 is F-No. 4. Qualification with F4 also qualifies the lower F-numbers, but only with backing.',
    evidence: [
      ev('weld_data_record', 'Filler metal type', 'E-7018', 1, {
        x0: 0.36, y0: 0.42, x1: 0.46, y1: 0.62,
      }),
      ev('weld_data_record', 'Specification', 'SFA 5.1', 1, {
        x0: 0.47, y0: 0.45, x1: 0.56, y1: 0.49,
      }),
      ev('requisition', 'Electrode', 'E-7018', 1, {
        x0: 0.2, y0: 0.36, x1: 0.29, y1: 0.383,
      }),
    ],
    state: 'derived',
    rule_verified: false,
  },
  {
    id: 'three_layers',
    variable: 'Three layers minimum',
    group: 'variables',
    actual: 'Yes — 6 passes recorded',
    derived: 'Yes',
    clause_ref: 'QW-452.1(b)',
    rule_note:
      'Derived from the pass count on the weld data record, not from a tickbox. Six passes (root, stabilising, fill 1-3, capping) is three or more layers, which lifts the 2t thickness cap.',
    evidence: [
      ev('weld_data_record', 'Weld passes', 'Root, Stabilising, Fill 1, Fill 2, Fill 3, Capping', 1, {
        x0: 0.05, y0: 0.42, x1: 0.2, y1: 0.62,
      }, 0.96),
    ],
    state: 'derived',
    rule_verified: false,
  },
  {
    id: 'thickness_qualified',
    variable: 'Deposit thickness qualified',
    group: 'variables',
    actual: '16 mm',
    derived: null,
    clause_ref: 'QW-451.1',
    evidence: [
      ev('requisition', 'Coupon size', 'Plate 150×150×16 mm', 1, {
        x0: 0.41, y0: 0.36, x1: 0.56, y1: 0.4,
      }),
      ev('weld_data_record', 'Wall thickness', '16 mm thk', 1, {
        x0: 0.72, y0: 0.45, x1: 0.85, y1: 0.49,
      }),
    ],
    state: 'blocked',
    blocked_reason:
      'QW-451.1 needs the bend test count confirmed against coupon thickness before the range can be stated. The lab report records two side bends; a 16 mm coupon requires two side bends, so this is likely "max. to be welded" — but the rule row is not encoded yet and Complyx will not state a range it cannot cite.',
    rule_verified: false,
  },
  {
    id: 'position',
    variable: 'Position qualified',
    group: 'variables',
    actual: '3G groove, plate',
    derived:
      'Plate and pipe over 610 mm OD: F, V. Pipe 73–610 mm OD: F. Fillet: F, H, V.',
    clause_ref: 'QW-461.9',
    rule_note:
      'A 3G groove coupon on plate qualifies flat and vertical on plate and large-bore pipe, flat only on smaller pipe, and all of F/H/V for fillet welds.',
    evidence: [
      ev('requisition', 'Position', '3G', 1, {
        x0: 0.29, y0: 0.36, x1: 0.34, y1: 0.383,
      }),
      ev('weld_data_record', 'Test position', '3G (Uphill)', 1, {
        x0: 0.2, y0: 0.28, x1: 0.35, y1: 0.31,
      }),
    ],
    state: 'derived',
    rule_verified: false,
  },
  {
    id: 'progression',
    variable: 'Vertical progression',
    group: 'variables',
    actual: 'Uphill',
    derived: 'Uphill only',
    clause_ref: 'QW-405.3',
    rule_note:
      'A change in vertical progression is an essential variable. Welding uphill qualifies uphill only.',
    evidence: [
      ev('weld_data_record', 'Direction of welding (all passes)', 'Up Hill ×6', 1, {
        x0: 0.3, y0: 0.42, x1: 0.36, y1: 0.62,
      }),
    ],
    state: 'derived',
    rule_verified: false,
  },
  {
    id: 'backing',
    variable: 'Backing',
    group: 'variables',
    actual: 'Welded without backing',
    derived: 'With and without backing',
    clause_ref: 'QW-402.4',
    rule_note:
      'A coupon welded without backing qualifies the welder both with and without. The reverse is not true.',
    evidence: [
      ev('requisition', 'Joint design / backing', 'Groove, N/A', 1, {
        x0: 0.62, y0: 0.36, x1: 0.72, y1: 0.383,
      }),
      ev('weld_data_record', 'Type of bevel', "Single 'V' Groove", 1, {
        x0: 0.55, y0: 0.3, x1: 0.72, y1: 0.33,
      }),
    ],
    state: 'derived',
    rule_verified: false,
  },
  {
    id: 'polarity',
    variable: 'Current and polarity',
    group: 'variables',
    actual: 'DCEP',
    derived: 'DCEP',
    clause_ref: 'QW-409',
    rule_note: 'Not an essential variable for welder performance qualification. Recorded for information.',
    evidence: [
      ev('weld_data_record', 'Polarity (all passes)', 'DCEP ×6', 1, {
        x0: 0.46, y0: 0.42, x1: 0.54, y1: 0.62,
      }),
    ],
    state: 'derived',
    rule_verified: false,
  },

  /* ---------------- testing ---------------- */
  {
    id: 'visual',
    variable: 'Visual examination (QW-302.4)',
    group: 'testing',
    actual: 'Acceptable',
    derived: null,
    clause_ref: 'QW-302.4',
    evidence: [
      ev('weld_data_record', 'Visual examination', 'Root: Acceptable / Final cap: Acceptable', 1, {
        x0: 0.05, y0: 0.66, x1: 0.45, y1: 0.7,
      }),
    ],
    state: 'derived',
    rule_verified: true,
  },
  {
    id: 'bend_test',
    variable: 'Side bend test (QW-462.2)',
    group: 'testing',
    actual: '2 side bends — both satisfactory',
    derived: null,
    clause_ref: 'QW-163',
    rule_note:
      'QW-163 acceptance: no open discontinuity exceeding 3 mm in the weld or heat-affected zone.',
    evidence: [
      ev('lab_report', 'Test result', 'Satisfactory ×2', 2, {
        x0: 0.5, y0: 0.4, x1: 0.75, y1: 0.5,
      }, 0.9),
    ],
    state: 'derived',
    rule_verified: false,
  },
  {
    id: 'lab',
    variable: 'Mechanical tests conducted by',
    group: 'certification',
    actual: 'Star Wire (India) Laboratories Pvt. Ltd.',
    derived: null,
    clause_ref: null,
    evidence: [
      ev('lab_report', 'Issuing laboratory', 'STAR WIRE (INDIA) LABORATORIES PVT. LTD.', 1, {
        x0: 0.18, y0: 0.06, x1: 0.7, y1: 0.1,
      }),
    ],
    state: 'derived',
    rule_verified: true,
  },
  {
    id: 'lab_report_no',
    variable: 'Laboratory test no.',
    group: 'certification',
    actual: null,
    derived: null,
    clause_ref: null,
    evidence: [],
    state: 'conflicted',
    blocked_reason:
      'The lab report carries two candidate reference numbers and Complyx cannot tell which is the report number. Enter it from the document.',
    rule_verified: true,
  },
];

export const DRAFT: WpqrDraft = {
  id: 'draft-139',
  coupon_no: 'WQT-139',
  welder_name: 'Devendra Singh',
  welder_id: 'TPL/GHAVP/W-72',
  form_no: 'FQ/069',
  form_rev: 'Rev.2',
  code_edition: 'ASME BPVC.IX-2021',
  kb_version: 'sec-ix/0.1-unverified',
  cells: CELLS,
  sources: SOURCES,
};

/** Agreement across the three sources. Precondition for trusting any cell. */
export const SOURCE_AGREEMENT = [
  {
    field: 'Welder name',
    values: {
      requisition: 'Devendra Singh',
      weld_data_record: 'DEVENDRA SINGH',
      lab_report: null,
    },
    agrees: true,
  },
  {
    field: 'Coupon number',
    values: {
      requisition: null,
      weld_data_record: 'WQT-139',
      lab_report: 'WQT-139',
    },
    agrees: true,
  },
  {
    field: 'WPS number',
    values: {
      requisition: 'WPS-01 R-0',
      weld_data_record: 'WPS-01 R-0',
      lab_report: null,
    },
    agrees: true,
  },
  {
    field: 'Position',
    values: {
      requisition: '3G',
      weld_data_record: '3G (Uphill)',
      lab_report: null,
    },
    agrees: true,
  },
  {
    field: 'Electrode',
    values: {
      requisition: 'E-7018',
      weld_data_record: 'E-7018',
      lab_report: null,
    },
    agrees: true,
  },
  {
    field: 'Coupon thickness',
    values: {
      requisition: '16 mm',
      weld_data_record: '16 mm',
      lab_report: '16 mm',
    },
    agrees: true,
  },
  {
    field: 'Base metal',
    values: {
      requisition: 'IS 2062 E250 Gr.BR',
      weld_data_record: 'IS 2062 E250 Gr.BR',
      lab_report: 'IS 2062 E250 Gr.BR',
    },
    agrees: true,
  },
  {
    field: 'Date',
    values: {
      requisition: '10.08.2026 (requested)',
      weld_data_record: '18.03.2026 (welded)',
      lab_report: '25.03.2026 (tested)',
    },
    agrees: true,
  },
] as const;
