'use client';
import { useEffect, useState, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import AppShell from '@/components/AppShell';
import StatusBadge from '@/components/StatusBadge';
import { getRecords, bulkApprove } from '@/lib/api';

const SOURCE_LABELS: Record<string, string> = {
  SAP_FUEL: 'SAP Fuel', UTILITY_ELECTRICITY: 'Electricity', TRAVEL_CONCUR: 'Travel'
};

export default function RecordsContent() {
  const sp = useSearchParams();
  const router = useRouter();
  const [records, setRecords] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkLoading, setBulkLoading] = useState(false);

  const [filters, setFilters] = useState({
    review_status: sp.get('review_status') || '',
    scope: sp.get('scope') || '',
    source_type: sp.get('source_type') || '',
    job: sp.get('job') || '',
  });

  const load = useCallback(() => {
    setLoading(true);
    const params: Record<string, string> = {};
    Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v; });
    getRecords(params).then(r => setRecords(r.data)).finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  const toggleSelect = (id: string) => {
    setSelected(prev => {
      const n = new Set(prev);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  };

  const toggleAll = () => {
    const approvable = records.filter(r => !r.is_locked).map(r => String(r.id));
    if (selected.size === approvable.length) setSelected(new Set());
    else setSelected(new Set(approvable));
  };

  const handleBulkApprove = async () => {
    if (!selected.size) return;
    setBulkLoading(true);
    try {
      await bulkApprove(Array.from(selected));
      setSelected(new Set());
      load();
    } finally { setBulkLoading(false); }
  };

  const approvable = records.filter(r => !r.is_locked);

  return (
    <AppShell>
      <div className="topbar">
        <div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Review</div>
          <div style={{ fontWeight: 700 }}>Emission Records</div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {selected.size > 0 && (
            <button className="btn btn-primary btn-sm" onClick={handleBulkApprove} disabled={bulkLoading}>
              {bulkLoading ? '…' : `✓ Approve ${selected.size} selected`}
            </button>
          )}
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {records.length} record{records.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      <div className="page-content">
        <div className="filters-bar">
          <select className="filter-select" value={filters.review_status}
            onChange={e => setFilters(f => ({ ...f, review_status: e.target.value }))}>
            <option value="">All statuses</option>
            <option value="PENDING_REVIEW">Pending Review</option>
            <option value="FLAGGED">Flagged</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
          </select>
          <select className="filter-select" value={filters.scope}
            onChange={e => setFilters(f => ({ ...f, scope: e.target.value }))}>
            <option value="">All scopes</option>
            <option value="SCOPE_1">Scope 1</option>
            <option value="SCOPE_2">Scope 2</option>
            <option value="SCOPE_3">Scope 3</option>
          </select>
          <select className="filter-select" value={filters.source_type}
            onChange={e => setFilters(f => ({ ...f, source_type: e.target.value }))}>
            <option value="">All sources</option>
            <option value="SAP_FUEL">SAP Fuel</option>
            <option value="UTILITY_ELECTRICITY">Electricity</option>
            <option value="TRAVEL_CONCUR">Travel</option>
          </select>
          {(filters.review_status || filters.scope || filters.source_type || filters.job) && (
            <button className="btn btn-ghost btn-sm"
              onClick={() => setFilters({ review_status: '', scope: '', source_type: '', job: '' })}>
              ✕ Clear filters
            </button>
          )}
        </div>

        {loading ? (
          <div className="loading-spinner"><div className="spinner" /></div>
        ) : records.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">✓</div>
            <div className="empty-text">No records match these filters</div>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 40 }}>
                    <input type="checkbox" className="checkbox"
                      checked={selected.size === approvable.length && approvable.length > 0}
                      onChange={toggleAll} />
                  </th>
                  <th>Description</th>
                  <th>Scope</th>
                  <th>Source</th>
                  <th>Activity</th>
                  <th>CO₂e (kg)</th>
                  <th>Period</th>
                  <th>Review</th>
                  <th>Flags</th>
                </tr>
              </thead>
              <tbody>
                {records.map(r => {
                  const isSuspicious = r.raw_row_status === 'SUSPICIOUS';
                  const warnings = (r.raw_warnings as string[]) || [];
                  return (
                    <tr key={String(r.id)}
                      className={selected.has(String(r.id)) ? 'selected' : ''}
                      onClick={() => router.push(`/records/${r.id}`)}>
                      <td onClick={e => e.stopPropagation()}>
                        {!r.is_locked ? (
                          <input type="checkbox" className="checkbox"
                            checked={selected.has(String(r.id))}
                            onChange={() => toggleSelect(String(r.id))} />
                        ) : (
                          <span style={{ color: 'var(--green-500)', fontSize: '0.8rem' }}>🔒</span>
                        )}
                      </td>
                      <td className="td-primary" style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {String(r.activity_description)}
                      </td>
                      <td><StatusBadge status={String(r.scope)} type="scope" /></td>
                      <td style={{ fontSize: '0.78rem' }}>{SOURCE_LABELS[String(r.source_type)] || String(r.source_type)}</td>
                      <td className="td-mono">
                        {Number(r.activity_value).toLocaleString()} {String(r.activity_unit)}
                      </td>
                      <td className="td-mono" style={{ color: 'var(--green-400)', fontWeight: 600 }}>
                        {Number(r.co2e_kg).toFixed(2)}
                      </td>
                      <td style={{ fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                        {r.data_period_start ? String(r.data_period_start) : '—'}
                      </td>
                      <td><StatusBadge status={String(r.review_status)} type="review" /></td>
                      <td>
                        {isSuspicious && (
                          <span title={warnings.join('\n')}
                            style={{ cursor: 'help', color: 'var(--amber-400)', fontSize: '0.85rem' }}>
                            ⚑ {warnings.length}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
