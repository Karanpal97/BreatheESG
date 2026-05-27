interface StatusBadgeProps {
  status: string;
  type?: 'review' | 'job' | 'parse' | 'scope';
}

const REVIEW_MAP: Record<string, [string, string]> = {
  PENDING_REVIEW: ['badge-dk-amber', '◷ Pending'],
  FLAGGED:        ['badge-dk-red',   '⚑ Flagged'],
  APPROVED:       ['badge-dk-green', '✓ Approved'],
  REJECTED:       ['badge-dk-red',   '✕ Rejected'],
};
const JOB_MAP: Record<string, [string, string]> = {
  PENDING:    ['badge-dk-gray',  '◷ Pending'],
  PROCESSING: ['badge-dk-blue',  '⟳ Processing'],
  DONE:       ['badge-dk-green', '✓ Done'],
  FAILED:     ['badge-dk-red',   '✕ Failed'],
};
const PARSE_MAP: Record<string, [string, string]> = {
  OK:         ['badge-dk-green', '✓ OK'],
  SUSPICIOUS: ['badge-dk-amber', '⚑ Suspicious'],
  FAILED:     ['badge-dk-red',   '✕ Failed'],
};
const SCOPE_MAP: Record<string, [string, string]> = {
  SCOPE_1: ['badge-dk-red',    'Scope 1'],
  SCOPE_2: ['badge-dk-blue',   'Scope 2'],
  SCOPE_3: ['badge-dk-amber',  'Scope 3'],
};

export default function StatusBadge({ status, type = 'review' }: StatusBadgeProps) {
  const map = type === 'job' ? JOB_MAP : type === 'parse' ? PARSE_MAP : type === 'scope' ? SCOPE_MAP : REVIEW_MAP;
  const [cls, label] = map[status] || ['badge-dk-gray', status];
  return <span className={`badge ${cls}`}>{label}</span>;
}
