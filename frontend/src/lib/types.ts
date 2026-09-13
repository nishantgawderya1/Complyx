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

/* ------------------------------------------------------------------ *
 * WPQR generation — three source documents in, one draft record out.
 *
 * This is a different job to checking a filled WPQR, and the types say so.
 * There is no `stated` value to compare against: the record does not exist
 * yet. What replaces it is an evidence chain, because an inspector signing a
 * record they did not transcribe needs to see where every value came from and
 * which rule turned it into a range.
 * ------------------------------------------------------------------ */

/** The three raw documents that feed a WPQR. */
export type SourceSlot = 'requisition' | 'weld_data_record' | 'lab_report';

export const SOURCE_SLOTS: SourceSlot[] = [
  'requisition',
  'weld_data_record',
  'lab_report',
];

export const SLOT_LABEL: Record<SourceSlot, string> = {
  requisition: 'Requisition sheet',
  weld_data_record: 'Weld data record',
  lab_report: 'Lab test report',
};

export const SLOT_FORMAT: Record<SourceSlot, string> = {
  requisition: 'NPCIL/QMD/TF/216',
  weld_data_record: 'NPCIL/QMD/TF-114 R0',
  lab_report: 'SWILPL/7.8F/01',
};

export type UploadState =
  | 'empty'
  | 'uploading'
  | 'classifying'
  | 'matched'
  | 'template_unknown'
  | 'rejected';

export interface UploadedFile {
  slot: SourceSlot | null;
  filename: string;
  size_bytes: number;
  state: UploadState;
  /** What the classifier read off the page, mangled exactly as printed. */
  raw_format_text?: string;
  canonical_key?: string;
  confidence?: number;
  page_count?: number;
  /** Why a file was rejected or could not be placed. Always human-readable. */
  reason?: string;
}

/**
 * One link in an evidence chain.
 *
 * An inspector signing a generated record must be able to answer "where did
 * this come from" for every value without leaving the screen. A clause
 * reference alone does not do that -- it says which rule applied, not what the
 * rule was applied to.
 */
export interface Evidence {
  slot: SourceSlot;
  field_label: string;
  value: string;
  page: number;
  bbox: BBox | null;
  confidence: number;
  read_method: ReadMethod;
}

export type CellState =
  /** Derived cleanly from verified inputs and a rule. Awaiting sign-off. */
  | 'derived'
  /** Confirmed by a named person. */
  | 'confirmed'
  /** A required input is missing, disputed or unreadable. Cannot derive. */
  | 'blocked'
  /** Sources disagree on the input, so the derivation is not trustworthy. */
  | 'conflicted';

/** One row of the generated WPQR. */
export interface WpqrCell {
  id: string;
  /** QW-484A variable name, as the form prints it. */
  variable: string;
  /** Section of the form this row belongs to. */
  group: 'identification' | 'variables' | 'testing' | 'certification';
  /** The transcribed actual value. */
  actual: string | null;
  /** The qualified range, computed from the rule tables. Never transcribed. */
  derived: string | null;
  clause_ref: string | null;
  /** Where `actual` came from. Empty for rows derived from other rows. */
  evidence: Evidence[];
  /** Plain sentence explaining the rule that produced `derived`. */
  rule_note?: string;
  state: CellState;
  blocked_reason?: string;
  /** False when the governing rule row is not reviewer-signed. */
  rule_verified: boolean;
  confirmed_by?: string;
  confirmed_at?: string;
  /**
   * True when a person typed this value because Complyx could not derive it.
   * It carries to the issued record: a reader must be able to tell which cells
   * the system stands behind and which a human supplied.
   */
  manual_entry?: boolean;
}

/**
 * A WPQR under construction.
 *
 * `status` never reaches a signed state while any cell is unconfirmed or
 * blocked. That is enforced in the UI and must be enforced again server-side:
 * this document, once signed, is what a welder's qualification rests on.
 */
export interface WpqrDraft {
  id: string;
  coupon_no: string | null;
  welder_name: string | null;
  welder_id: string | null;
  form_no: string;
  form_rev: string;
  /** Which edition of Section IX the rule tables were read from. */
  code_edition: string;
  kb_version: string;
  cells: WpqrCell[];
  sources: UploadedFile[];
  signed_by?: string;
  signed_at?: string;
}

export const CELL_STATE_LABEL: Record<CellState, string> = {
  derived: 'Unsigned',
  confirmed: 'Signed',
  blocked: 'Cannot derive',
  conflicted: 'Sources disagree',
};
