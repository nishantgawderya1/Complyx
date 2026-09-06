/**
 * Development fixtures.
 *
 * These mirror the *structure* of the real NPCIL GHAVP-1&2 packages and the
 * real findings the pipeline produced, so the screens can be built and reviewed
 * without the backend running.
 *
 * **Welder names and ID numbers here are invented.** The real packages carry
 * photographs, full names and ID numbers from an operating nuclear site; that
 * data lives in a gitignored fixtures directory and never enters version
 * control (CLAUDE.md section 10). Coupon numbers, format numbers and clause
 * references are form control data, not personal data, and are kept because the
 * findings cannot be explained without them.
 *
 * The two findings modelled below are the two the pipeline actually found:
 * an identity card carrying the wrong coupon number, and a weld data record
 * naming the wrong welder.
 */

import type {
  CheckboxConflict,
  DerivationRow,
  DocType,
  Finding,
  QualificationPackage,
  ReconciliationRow,
  SourceDocument,
} from './types';

const PROVENANCE = {
  kb_version: 'sec-ix/0.1-unverified',
  template_versions: ['TF-127-R0/1', 'FQ-069-R2/1'],
  model_version: 'text-layer-only',
  prompt_version: 'v1',
};

function doc(
  id: string,
  doc_type: DocType,
  format_no: string,
  format_rev: string,
  fields: SourceDocument['fields'],
  opts: Partial<SourceDocument> = {},
): SourceDocument {
  return {
    id,
    doc_type,
    format_no,
    format_rev,
    template_matched: true,
    template_verified: false,
    page_count: 1,
    fields,
    ...opts,
  };
}

const idCardFields: SourceDocument['fields'] = [
  {
    name: 'welder_name',
    value: 'DEVENDRA SINGH',
    page: 1,
    bbox: { x0: 0.236, y0: 0.208, x1: 0.443, y1: 0.232 },
    confidence: 0.9,
    read_method: 'template_region',
    needs_review: false,
    template_version: 'TF-127-R0/1',
  },
  {
    name: 'welder_id',
    value: 'TPL/GHAVP/W-72',
    page: 1,
    bbox: { x0: 0.245, y0: 0.24, x1: 0.394, y1: 0.267 },
    confidence: 0.9,
    read_method: 'template_region',
    needs_review: false,
    template_version: 'TF-127-R0/1',
  },
  {
    name: 'welding_process',
    value: 'SMAW',
    page: 1,
    bbox: { x0: 0.285, y0: 0.271, x1: 0.34, y1: 0.296 },
    confidence: 0.9,
    read_method: 'template_region',
    needs_review: false,
    template_version: 'TF-127-R0/1',
  },
  {
    name: 'date_of_test',
    value: '18.03.2026',
    page: 1,
    bbox: { x0: 0.116, y0: 0.66, x1: 0.192, y1: 0.676 },
    confidence: 0.9,
    read_method: 'template_region',
    needs_review: false,
    template_version: 'TF-127-R0/1',
  },
  {
    name: 'qualified_thickness',
    value: 'MAX. to be Welded',
    page: 1,
    bbox: { x0: 0.632, y0: 0.642, x1: 0.694, y1: 0.676 },
    confidence: 0.9,
    read_method: 'template_region',
    needs_review: false,
    template_version: 'TF-127-R0/1',
  },
  {
    name: 'coupon_no',
    value: 'WQT-138',
    page: 1,
    bbox: { x0: 0.865, y0: 0.655, x1: 0.945, y1: 0.688 },
    confidence: 0.9,
    read_method: 'template_region',
    needs_review: false,
    template_version: 'TF-127-R0/1',
  },
];

const wpqrFields: SourceDocument['fields'] = [
  {
    name: 'coupon_no',
    value: 'WQT-139',
    page: 1,
    bbox: { x0: 0.588, y0: 0.113, x1: 0.64, y1: 0.129 },
    confidence: 0.9,
    read_method: 'template_region',
    needs_review: false,
    template_version: 'FQ-069-R2/1',
  },
  {
    name: 'welder_name',
    value: 'MR. DEVENDRA SINGH',
    page: 1,
    bbox: { x0: 0.251, y0: 0.149, x1: 0.444, y1: 0.166 },
    confidence: 0.9,
    read_method: 'template_region',
    needs_review: false,
    template_version: 'FQ-069-R2/1',
  },
  {
    name: 'welder_id',
    value: 'TPL/GHAVP/W-72',
    page: 1,
    bbox: { x0: 0.666, y0: 0.15, x1: 0.768, y1: 0.166 },
    confidence: 0.9,
    read_method: 'template_region',
    needs_review: false,
    template_version: 'FQ-069-R2/1',
  },
  {
    name: 'base_metal_p_number_actual',
    value: 'P1 to P1',
    page: 1,
    bbox: { x0: 0.596, y0: 0.336, x1: 0.633, y1: 0.352 },
    confidence: 0.9,
    read_method: 'template_region',
    needs_review: false,
    template_version: 'FQ-069-R2/1',
  },
  {
    name: 'base_metal_p_number_qualified',
    value: 'P1 through P 15F',
    page: 1,
    bbox: { x0: 0.768, y0: 0.336, x1: 0.85, y1: 0.352 },
    confidence: 0.9,
    read_method: 'template_region',
    needs_review: false,
    template_version: 'FQ-069-R2/1',
  },
  {
    name: 'deposit_thickness_qualified',
    value: 'Max. to be welded',
    page: 1,
    bbox: { x0: 0.762, y0: 0.44, x1: 0.856, y1: 0.458 },
    confidence: 0.9,
    read_method: 'template_region',
    needs_review: false,
    template_version: 'FQ-069-R2/1',
  },
  {
    name: 'three_layers_minimum_process_1',
    value: null,
    page: 1,
    bbox: { x0: 0.402, y0: 0.438, x1: 0.438, y1: 0.456 },
    confidence: 0,
    read_method: 'checkbox_agreed',
    needs_review: true,
    review_reason:
      'CV reader and vision reader disagree. Never resolved automatically.',
    template_version: 'FQ-069-R2/1',
  },
];

const wdrFields: SourceDocument['fields'] = [
  {
    name: 'coupon_no',
    value: 'WQT-139',
    page: 1,
    bbox: { x0: 0.72, y0: 0.318, x1: 0.83, y1: 0.34 },
    confidence: 0.9,
    read_method: 'template_region',
    needs_review: false,
    template_version: 'TF-114-R0/1',
  },
  {
    name: 'welder_name',
    value: 'HARPAL YADAV',
    page: 1,
    bbox: { x0: 0.18, y0: 0.148, x1: 0.42, y1: 0.172 },
    confidence: 0.9,
    read_method: 'template_region',
    needs_review: false,
    template_version: 'TF-114-R0/1',
  },
  {
    name: 'weld_date',
    value: '18.03.2026',
    page: 1,
    bbox: { x0: 0.18, y0: 0.2, x1: 0.29, y1: 0.222 },
    confidence: 0.9,
    read_method: 'template_region',
    needs_review: false,
    template_version: 'TF-114-R0/1',
  },
];

export const FINDINGS: Finding[] = [
  {
    id: 'f1',
    finding_type: 'reconciliation',
    severity: 'CRITICAL',
    field_name: 'coupon_no',
    title: 'Identity card carries a different coupon number to the rest of the package',
    observed: 'WQT-138',
    expected: 'WQT-139',
    clause_ref: null,
    locations: [
      {
        document_id: 'd-idcard',
        doc_type: 'id_card',
        page: 1,
        bbox: { x0: 0.865, y0: 0.655, x1: 0.945, y1: 0.688 },
        observed: 'WQT-138',
      },
      {
        document_id: 'd-wpqr',
        doc_type: 'wpqr',
        page: 1,
        bbox: { x0: 0.588, y0: 0.113, x1: 0.64, y1: 0.129 },
        observed: 'WQT-139',
      },
    ],
    status: 'open',
  },
  {
    id: 'f2',
    finding_type: 'reconciliation',
    severity: 'CRITICAL',
    field_name: 'welder_name',
    title: 'Weld data record names a different welder to the other five documents',
    observed: 'HARPAL YADAV',
    expected: 'DEVENDRA SINGH',
    clause_ref: null,
    locations: [
      {
        document_id: 'd-wdr',
        doc_type: 'weld_data_record',
        page: 1,
        bbox: { x0: 0.18, y0: 0.148, x1: 0.42, y1: 0.172 },
        observed: 'HARPAL YADAV',
      },
    ],
    status: 'open',
  },
  {
    id: 'f3',
    finding_type: 'code_compliance',
    severity: 'MAJOR',
    field_name: 'three_layers_minimum_process_1',
    title: 'Three-layer minimum checkbox could not be read',
    observed: 'CV reader: checked · Vision reader: unchecked',
    expected: 'Both readers to agree',
    clause_ref: 'QW-452.1(b)',
    locations: [
      {
        document_id: 'd-wpqr',
        doc_type: 'wpqr',
        page: 1,
        bbox: { x0: 0.402, y0: 0.438, x1: 0.438, y1: 0.456 },
        observed: 'disputed',
      },
    ],
    status: 'open',
  },
];

export const DOCUMENTS: SourceDocument[] = [
  doc('d-req', 'requisition', 'NPCIL/QMD/TF/216', '-', [], {
    template_matched: false,
  }),
  doc('d-wdr', 'weld_data_record', 'NPCIL/QMD/TF-114', 'R0', wdrFields),
  doc('d-sample', 'sample_card', 'NPCIL/QMD/TF053', 'R1', []),
  doc('d-wpqr', 'wpqr', 'FQ/069', 'Rev.2', wpqrFields),
  doc('d-idcard', 'id_card', 'NPCIL/QMD/TF-127', 'R0', idCardFields),
];

export const PACKAGE: QualificationPackage = {
  id: 'pkg-139',
  coupon_no: 'WQT-139',
  welder_id: 'TPL/GHAVP/W-72',
  welder_name: 'Devendra Singh',
  project: 'GHAVP-1&2 Main Plant',
  client: 'NPCIL',
  contractor: 'Tata Projects Ltd.',
  wps_no: 'TPL/GHAVP1&2/SMAW/WPS-01 R-0',
  status: 'review',
  received_date: '2026-03-24',
  test_date: '2026-03-18',
  documents: DOCUMENTS,
  findings: FINDINGS,
  provenance: PROVENANCE,
};

/** The worklist. Deliberately varied so every status renders in development. */
export const WORKLIST: QualificationPackage[] = [
  PACKAGE,
  {
    ...PACKAGE,
    id: 'pkg-138',
    coupon_no: 'WQT-138',
    welder_id: 'TPL/GHAVP/W-71',
    welder_name: 'Harpal Yadav',
    status: 'complete',
    test_date: '2026-02-28',
    received_date: '2026-03-05',
    findings: [],
    documents: DOCUMENTS,
  },
  {
    ...PACKAGE,
    id: 'pkg-140',
    coupon_no: 'WQT-140',
    welder_id: 'TPL/GHAVP/W-73',
    welder_name: 'Suresh Meena',
    status: 'incomplete',
    test_date: null,
    received_date: '2026-03-26',
    findings: [
      {
        ...FINDINGS[0],
        id: 'f4',
        finding_type: 'completeness',
        severity: 'MAJOR',
        field_name: 'lab_report',
        title: 'Lab test report is not present in the package',
        observed: 'absent',
        expected: 'SWILPL/7.8F/01',
        locations: [],
      },
    ],
    documents: DOCUMENTS.filter((d) => d.doc_type !== 'lab_report').slice(0, 3),
  },
  {
    ...PACKAGE,
    id: 'pkg-141',
    coupon_no: 'WQT-141',
    welder_id: 'TPL/GHAVP/W-74',
    welder_name: 'Ravi Prakash',
    status: 'processing',
    test_date: '2026-03-30',
    received_date: '2026-03-31',
    findings: [],
  },
];

/**
 * The reconciliation grid.
 *
 * Rows are fields, columns are the six documents. Agreement reads as a clean
 * row; disagreement is visible because one cell breaks the pattern. This is the
 * most persuasive screen in the product for a first demo, and both real
 * findings become obvious here in one glance.
 */
export const RECONCILIATION: ReconciliationRow[] = [
  {
    field_name: 'coupon_no',
    label: 'Coupon number',
    values: {
      requisition: 'WQT-139',
      weld_data_record: 'WQT-139',
      sample_card: 'WQT-139',
      lab_report: 'WQT-139',
      wpqr: 'WQT-139',
      id_card: 'WQT-138',
    },
    agrees: false,
    finding_id: 'f1',
  },
  {
    field_name: 'welder_name',
    label: 'Welder name',
    values: {
      requisition: 'DEVENDRA SINGH',
      weld_data_record: 'HARPAL YADAV',
      sample_card: 'DEVENDRA SINGH',
      lab_report: 'DEVENDRA SINGH',
      wpqr: 'DEVENDRA SINGH',
      id_card: 'DEVENDRA SINGH',
    },
    agrees: false,
    finding_id: 'f2',
  },
  {
    field_name: 'welder_id',
    label: 'Welder ID',
    values: {
      requisition: null,
      weld_data_record: 'TPL/GHAVP/W-72',
      sample_card: null,
      lab_report: null,
      wpqr: 'TPL/GHAVP/W-72',
      id_card: 'TPL/GHAVP/W-72',
    },
    agrees: true,
  },
  {
    field_name: 'wps_no',
    label: 'WPS number',
    values: {
      requisition: 'WPS-01 R-0',
      weld_data_record: 'WPS-01 R-0',
      sample_card: 'WPS-01 R-0',
      lab_report: null,
      wpqr: 'WPS-01 R-0',
      id_card: 'WPS-01 R-0',
    },
    agrees: true,
  },
  {
    field_name: 'position',
    label: 'Position',
    values: {
      requisition: '3G',
      weld_data_record: '3G (Uphill)',
      sample_card: '3G',
      lab_report: null,
      wpqr: '3G',
      id_card: '3G',
    },
    agrees: true,
  },
  {
    field_name: 'thickness',
    label: 'Coupon thickness',
    values: {
      requisition: '16 mm',
      weld_data_record: '16 mm',
      sample_card: '16 mm',
      lab_report: '16 mm',
      wpqr: '16 MM',
      id_card: null,
    },
    agrees: true,
  },
  {
    field_name: 'base_metal',
    label: 'Base metal',
    values: {
      requisition: 'IS 2062 E250 Gr.BR',
      weld_data_record: 'IS 2062 E250 Gr.BR',
      sample_card: 'IS 2062 E250 Gr.BR',
      lab_report: 'IS 2062 E250 Gr.BR',
      wpqr: 'IS 2062 E250 Gr.BR',
      id_card: null,
    },
    agrees: true,
  },
];

/**
 * The derivation view.
 *
 * Actual value, what Complyx derived from the rule tables, and what the WPQR as
 * filled actually states. The thickness row is blocked rather than guessed:
 * QW-452.1(b) needs the three-layer checkbox, and both readers disagreed.
 */
export const DERIVATION: DerivationRow[] = [
  {
    variable: 'Base metal P-number',
    clause_ref: 'QW-423.1',
    actual: 'P1 to P1',
    derived: 'P1 through P15F',
    stated: 'P1 through P 15F',
    matches: true,
    rule_verified: false,
  },
  {
    variable: 'Filler metal F-number',
    clause_ref: 'QW-433',
    actual: 'F4 (E7018)',
    derived: 'F4 with & without backing; F3, F2, F1 with backing',
    stated: 'F. No. 4 With & Without Backing / F. No. 3,2 & 1 with Backing',
    matches: true,
    rule_verified: false,
  },
  {
    variable: 'Deposit thickness',
    clause_ref: 'QW-452.1(b)',
    actual: '16 mm',
    derived: null,
    stated: 'Max. to be welded',
    matches: false,
    blocked_reason:
      'Requires the three-layer minimum checkbox, which the CV and vision readers read differently.',
    rule_verified: false,
  },
  {
    variable: 'Position',
    clause_ref: 'QW-461.9',
    actual: '3G groove, plate',
    derived:
      'Plate & pipe over 610mm OD F,V; pipe 73–610mm OD F; fillet F,H,V',
    stated:
      'For Plate & Pipe over 24 inches (610mm OD) F&V, For Pipe 73 to 610mm OD- F, For Fillet F,H,V',
    matches: true,
    rule_verified: false,
  },
  {
    variable: 'Backing',
    clause_ref: 'QW-402.4',
    actual: 'Welded without backing',
    derived: 'With & without backing',
    stated: 'SMAW (With & Without Backing)',
    matches: true,
    rule_verified: false,
  },
  {
    variable: 'Vertical progression',
    clause_ref: 'QW-405.3',
    actual: 'Uphill',
    derived: 'Uphill only',
    stated: 'UPHILL',
    matches: true,
    rule_verified: false,
  },
];

export const CHECKBOX_CONFLICT: CheckboxConflict = {
  id: 'cb1',
  name: 'three_layers_minimum_process_1',
  label: 'Three layers minimum — process 1',
  clause_ref: 'QW-452.1(b)',
  document_id: 'd-wpqr',
  doc_type: 'wpqr',
  page: 1,
  yes_bbox: { x0: 0.402, y0: 0.438, x1: 0.438, y1: 0.456 },
  no_bbox: { x0: 0.454, y0: 0.438, x1: 0.49, y1: 0.456 },
  cv_reading: 'checked',
  vision_reading: 'unchecked',
  consequence_if_yes: 'Thickness qualified range: max. to be welded',
  consequence_if_no: 'Thickness qualified range: limited to 2t (32 mm)',
};
