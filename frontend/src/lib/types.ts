/**
 * Domain types, mirroring the backend Pydantic models.
 *
 * These follow `backend/models/template.py` and `docs/data-model.md`. Where a
 * name differs from the backend it is a bug, not a translation: the API returns
 * these shapes directly.
 */

/** The six document types that make up one qualification package. */
export type DocType =
  | 'requisition'
  | 'weld_data_record'
  | 'sample_card'
  | 'lab_report'
  | 'wpqr'
  | 'id_card';

/** Fixed order, matching the physical folder and the flow of the package. */
export const DOC_ORDER: DocType[] = [
  'requisition',
  'weld_data_record',
  'sample_card',
  'lab_report',
  'wpqr',
  'id_card',
];

export const DOC_LABEL: Record<DocType, string> = {
  requisition: 'Requisition',
  weld_data_record: 'Weld data record',
  sample_card: 'Sample card',
  lab_report: 'Lab report',
  wpqr: 'WPQR',
  id_card: 'Identity card',
};

/** The format number printed on each form, for the title block. */
export const DOC_FORMAT: Record<DocType, string> = {
  requisition: 'NPCIL/QMD/TF/216',
  weld_data_record: 'NPCIL/QMD/TF-114 R0',
  sample_card: 'NPCIL/QMD/TF053-R1',
  lab_report: 'SWILPL/7.8F/01',
  wpqr: 'FQ/069 Rev.2',
  id_card: 'NPCIL/QMD/TF-127 R0',
};

export type PackageStatus = 'incomplete' | 'processing' | 'review' | 'complete';

export type Severity = 'CRITICAL' | 'MAJOR' | 'MINOR';

export type FindingType =
  | 'reconciliation'
  | 'code_compliance'
  | 'derivation_mismatch'
  | 'completeness';

export type FindingStatus = 'open' | 'confirmed' | 'dismissed';

/**
 * How a value was obtained. Surfaced in the UI rather than logged, because a
 * value read from a fallback rectangle is materially less trustworthy than one
 * read from an anchored region and a reviewer must be able to tell.
 */
export type ReadMethod =
  | 'template_region'
  | 'template_region_fallback'
  | 'full_page'
  | 'checkbox_cv'
  | 'checkbox_vision'
  | 'checkbox_agreed';

/** Normalised page coordinates, 0..1. Origin top-left, matching PyMuPDF. */
export interface BBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface ExtractedField {
  name: string;
  value: string | null;
  unit?: string | null;
  page: number;
  bbox: BBox | null;
  confidence: number;
  read_method: ReadMethod;
  source_snippet?: string;
  needs_review: boolean;
  review_reason?: string;
  template_version: string | null;
}

export interface SourceDocument {
  id: string;
  doc_type: DocType;
  format_no: string;
  format_rev: string;
  /** False means the page fell back to whole-page extraction. Always shown. */
  template_matched: boolean;
  /** False means the template's regions are not reviewer-verified. */
  template_verified: boolean;
  page_count: number;
  fields: ExtractedField[];
}

export interface FindingLocation {
  document_id: string;
  doc_type: DocType;
  page: number;
  bbox: BBox;
  /** The value as it reads on that document. */
  observed: string;
}

export interface Finding {
  id: string;
  finding_type: FindingType;
  severity: Severity;
  field_name: string;
  /** Human sentence. What is wrong. */
  title: string;
  observed: string;
  expected: string;
  clause_ref: string | null;
  /** Every place this finding can be seen on a document. */
  locations: FindingLocation[];
  status: FindingStatus;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  dismiss_reason?: string | null;
}

export interface QualificationPackage {
  id: string;
  coupon_no: string;
  welder_id: string;
  welder_name: string;
  project: string;
  client: string;
  contractor: string;
  wps_no: string;
  status: PackageStatus;
  received_date: string;
  test_date: string | null;
  documents: SourceDocument[];
  findings: Finding[];
  /** Provenance stamped on every stored verdict. */
  provenance: {
    kb_version: string;
    template_versions: string[];
    model_version: string;
    prompt_version: string;
  };
}

/** One row of the reconciliation grid: a field across all six documents. */
export interface ReconciliationRow {
  field_name: string;
  label: string;
  /** Value per document type. Absent means the document does not carry it. */
  values: Partial<Record<DocType, string | null>>;
  /** True when every present value agrees after canonicalisation. */
  agrees: boolean;
  finding_id?: string;
}

/** One row of the derivation view: actual, derived, and what the WPQR says. */
export interface DerivationRow {
  variable: string;
  clause_ref: string;
  actual: string;
  /** What Complyx computed from the rule tables. */
  derived: string | null;
  /** What the filled WPQR actually states. */
  stated: string;
  matches: boolean;
  /** Set when the derivation could not be completed at all. */
  blocked_reason?: string;
  /** False when the governing rule row is not reviewer-verified. */
  rule_verified: boolean;
}

/** A checkbox whose two readers disagreed, awaiting a human. */
export interface CheckboxConflict {
  id: string;
  name: string;
  label: string;
  clause_ref: string;
  document_id: string;
  doc_type: DocType;
  page: number;
  yes_bbox: BBox;
  no_bbox: BBox;
  cv_reading: 'checked' | 'unchecked';
  vision_reading: 'checked' | 'unchecked';
  /** What each answer would make the qualified range say. */
  consequence_if_yes: string;
  consequence_if_no: string;
}

export const SEVERITY_ORDER: Record<Severity, number> = {
  CRITICAL: 0,
  MAJOR: 1,
  MINOR: 2,
};
