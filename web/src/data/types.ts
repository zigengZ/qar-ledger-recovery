export interface CountRaw {
  id: string;
  count: number;
  raw: string;
}

export interface TopRow {
  address: string;
  raw: string;
  role: string;
  p10: string;
  name: string;
  provider: string;
  confidence: string;
  changed: number;
}

export interface Overview {
  generated_at: string;
  process_id: string | null;
  as_of: string | null;
  nonce: number | null;
  block_height: number | null;
  epoch: string | null;
  decimals: number;
  supply_raw: string;
  supply_human: string;
  addresses: number;
  nonzero: number;
  zero: number;
  messages?: number | null;
  crons?: number | null;
  assignments?: number | null;
  handler_errors: number | null;
  memory_sha256: string | null;
  height_source?: string | null;
  goal_complete: boolean;
  not_a_claim_list: boolean;
  dry_run: boolean;
  classification: {
    source: string;
    pools_source: string;
    ledger_source: string;
    run_id: string | null;
    source_nonce: number | null;
    tail_reclass: string;
    missing_from_classification: number;
    balance_drift: number;
    pool_role_conflicts: number;
    note_zh: string;
    note_en: string;
  };
  concentration: { n: number | "rest"; count: number; raw: string }[];
  categories: CountRaw[];
  roles: CountRaw[];
  p10_classes: CountRaw[];
  histogram: CountRaw[];
  lorenz: { p: number; l: number }[];
  top: TopRow[];
}

export interface Manifest {
  generated_at: string;
  data_status: Record<string, string | number | boolean | null>;
  selected: Record<string, string | null>;
  checks: Record<string, string | number | boolean>;
  sources: { path: string | null; sha256: string; bytes: number; role: string; gitignored?: boolean; outside_repo?: boolean }[];
}

export interface EvidencePoint {
  label_zh: string;
  label_en: string;
  value: string | number | boolean | null;
  href: string | null;
}

export interface EvidenceStep {
  id: string;
  status: string;
  title_zh: string;
  title_en: string;
  summary_zh: string;
  summary_en: string;
  points: EvidencePoint[];
}

export interface Caveat {
  id: string;
  zh: string;
  en: string;
  source: string | null;
  source_text: string | null;
}

export interface Evidence {
  generated_at: string;
  process_id: string | null;
  timeline: EvidenceStep[];
  caveats: Caveat[];
  balance_drift: { address: string; tail_raw: string; snapshot_raw: string }[];
  unclassified_addresses: string[];
  links: Record<string, string | null>;
  canonical_balances?: CanonicalBalances;
}

export interface CanonicalBalances {
  status: string;
  sha256: string | null;
  field: string | null;
  source: string;
}

export interface MethodologyDoc {
  path: string;
  status: string;
  markdown: string | null;
}

export interface Methodology {
  generated_at: string;
  repo: string | null;
  documents: { en: MethodologyDoc; zh: MethodologyDoc };
}

export interface Holder {
  address: string;
  raw: string;
  role: string;
  p10: string;
  name: string;
  provider: string;
  confidence: string;
  changed: number;
  rank: number;
}

export interface LedgerData {
  list: Holder[];
  byAddress: Map<string, Holder>;
  supplyRaw: string;
  nonce: number | null;
  decimals: number;
}
