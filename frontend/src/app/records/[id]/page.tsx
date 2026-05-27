'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import AppShell from '@/components/AppShell';
import StatusBadge from '@/components/StatusBadge';
import { getRecord, approveRecord, rejectRecord, patchRecord, getAuditLog } from '@/lib/api';

export default function RecordDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [rec, setRec] = useState<Record<string, unknown> | null>(null);
  const [audit, setAudit] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'detail' | 'raw' | 'audit'>('detail');
  const [editing, setEditing] = useState(false);
  const [editNote, setEditNote] = useState('');
  const [editVal, setEditVal] = useState('');
  const [rejectNote, setRejectNote] = useState('');
  const [showReject, setShowReject] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    Promise.all([
      getRecord(id).then(r => setRec(r.data)),
      getAuditLog(id).then(r => setAudit(r.data)),
    ]).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const handleApprove = async () => {
    setSaving(true);
    try { await approveRecord(id); load(); } finally { setSaving(false); }
  };

  const handleReject = async () => {
    if (!rejectNote.trim()) { setError('Please provide a reason for rejection'); return; }
    setSaving(true);
    try { await rejectRecord(id, rejectNote); setShowReject(false); load(); }
    finally { setSaving(false); }
  };

  const handleEdit = async () => {
    if (!editVal || isNaN(Number(editVal))) { setError('Enter a valid number'); return; }
    setSaving(true);
    try {
      await patchRecord(id, { activity_value: Number(editVal), edit_note: editNote });
      setEditing(false); load();
    } finally { setSaving(false); }
  };

  if (loading) return (
    <AppShell>
      <div className="loading-spinner" style={{ minHeight: '60vh' }}><div className="spinner" /></div>
    </AppShell>
  );

  if (!rec) return (
    <AppShell>
      <div className="empty-state"><div className="empty-text">Record not found</div></div>
    </AppShell>
  );

  const isLocked = Boolean(rec.is_locked);
  const warnings = (rec.raw_warnings as string[]) || [];
  const rawRow = rec.raw_row as Record<string, unknown> | null;

  return (
    <AppShell>
      <div className="topbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-ghost btn-sm" onClick={() => router.back()}>← Back</button>
          <div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Record Detail</div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {String(rec.activity_description)}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <StatusBadge status={String(rec.scope)} type="scope" />
          <StatusBadge status={String(rec.review_status)} type="review" />
          {isLocked && <span className="badge badge-dk-green">🔒 Locked</span>}
        </div>
      </div>

      <div className="page-content">
        {error && <div className="alert alert-error">⚠ {error}</div>}

        {/* Warnings strip */}
        {warnings.length > 0 && (
          <div className="alert alert-warn" style={{ marginBottom: 20, flexDirection: 'column', alignItems: 'flex-start', gap: 4 }}>
            <strong>⚑ {warnings.length} parser warning{warnings.length > 1 ? 's' : ''}</strong>
            {warnings.map((w, i) => <div key={i} style={{ fontSize: '0.8rem' }}>· {w}</div>)}
          </div>
        )}

        {/* Action buttons */}
        {!isLocked && (
          <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
            <button className="btn btn-primary" onClick={handleApprove} disabled={saving}>
              ✓ Approve & Lock
            </button>
            <button className="btn btn-danger" onClick={() => setShowReject(!showReject)}>
              ✕ Reject
            </button>
            <button className="btn btn-secondary" onClick={() => { setEditing(!editing); setEditVal(String(rec.activity_value)); }}>
              ✎ Edit value
            </button>
          </div>
        )}

        {/* Reject form */}
        {showReject && !isLocked && (
          <div className="card" style={{ marginBottom: 16, borderColor: 'rgba(239,68,68,.3)' }}>
            <div style={{ fontWeight: 600, marginBottom: 10, color: 'var(--red-400)' }}>Reject record</div>
            <div className="form-group" style={{ marginBottom: 10 }}>
              <label>Reason for rejection *</label>
              <textarea placeholder="Explain why this record is being rejected…"
                value={rejectNote} onChange={e => setRejectNote(e.target.value)} rows={2} />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-danger btn-sm" onClick={handleReject} disabled={saving}>Confirm Reject</button>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowReject(false)}>Cancel</button>
            </div>
          </div>
        )}

        {/* Edit form */}
        {editing && !isLocked && (
          <div className="card" style={{ marginBottom: 16, borderColor: 'rgba(34,197,94,.3)' }}>
            <div style={{ fontWeight: 600, marginBottom: 10 }}>Edit activity value</div>
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' }}>
              <div className="form-group" style={{ marginBottom: 0, flex: '0 0 200px' }}>
                <label>Activity value ({String(rec.activity_unit)})</label>
                <input type="number" step="any" value={editVal} onChange={e => setEditVal(e.target.value)} />
              </div>
              <div className="form-group" style={{ marginBottom: 0, flex: 1 }}>
                <label>Edit note (required)</label>
                <input type="text" placeholder="Why are you changing this?" value={editNote}
                  onChange={e => setEditNote(e.target.value)} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <button className="btn btn-primary btn-sm" onClick={handleEdit} disabled={saving || !editNote.trim()}>
                Save changes
              </button>
              <button className="btn btn-ghost btn-sm" onClick={() => setEditing(false)}>Cancel</button>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 8 }}>
              CO₂e will be recalculated: new_value × {Number(rec.emission_factor).toFixed(5)} = {' '}
              {(Number(editVal || 0) * Number(rec.emission_factor)).toFixed(2)} kg CO₂e
            </div>
          </div>
        )}

        {/* Tab nav */}
        <div className="tabs">
          {(['detail', 'raw', 'audit'] as const).map(t => (
            <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
              {t === 'detail' ? 'Normalised data' : t === 'raw' ? 'Raw source row' : `Audit log (${audit.length})`}
            </button>
          ))}
        </div>

        {tab === 'detail' && (
          <div className="card">
            <div className="detail-grid">
              <div className="detail-item">
                <div className="detail-key">Scope</div>
                <div className="detail-val">{String(rec.scope_display)}</div>
              </div>
              {rec.scope_3_category && (
                <div className="detail-item">
                  <div className="detail-key">Scope 3 Category</div>
                  <div className="detail-val">{String(rec.scope_3_category)}</div>
                </div>
              )}
              <div className="detail-item">
                <div className="detail-key">Activity Value</div>
                <div className="detail-val mono">
                  {Number(rec.activity_value).toLocaleString(undefined, { maximumFractionDigits: 4 })} {String(rec.activity_unit)}
                </div>
              </div>
              <div className="detail-item">
                <div className="detail-key">CO₂e</div>
                <div className="detail-val mono" style={{ color: 'var(--green-400)', fontWeight: 700, fontSize: '1.1rem' }}>
                  {Number(rec.co2e_kg).toFixed(4)} kg CO₂e
                </div>
              </div>
              <div className="detail-item">
                <div className="detail-key">Emission Factor</div>
                <div className="detail-val mono">{Number(rec.emission_factor).toFixed(5)}</div>
              </div>
              <div className="detail-item">
                <div className="detail-key">EF Source</div>
                <div className="detail-val">{String(rec.emission_factor_source)}</div>
              </div>
              <div className="detail-item">
                <div className="detail-key">Period</div>
                <div className="detail-val">
                  {rec.data_period_start ? `${String(rec.data_period_start)} → ${String(rec.data_period_end || rec.data_period_start)}` : '—'}
                </div>
              </div>
              <div className="detail-item">
                <div className="detail-key">Source Document</div>
                <div className="detail-val mono">{String(rec.source_document_ref || '—')}</div>
              </div>
              {rec.plant_code && (
                <div className="detail-item">
                  <div className="detail-key">Plant Code</div>
                  <div className="detail-val mono">{String(rec.plant_code)}</div>
                </div>
              )}
              {rec.facility_name && (
                <div className="detail-item">
                  <div className="detail-key">Facility</div>
                  <div className="detail-val">{String(rec.facility_name)}</div>
                </div>
              )}
              {rec.cost_center && (
                <div className="detail-item">
                  <div className="detail-key">Cost Centre</div>
                  <div className="detail-val mono">{String(rec.cost_center)}</div>
                </div>
              )}
              {rec.department && (
                <div className="detail-item">
                  <div className="detail-key">Department</div>
                  <div className="detail-val">{String(rec.department)}</div>
                </div>
              )}
              {rec.reviewed_by && (
                <div className="detail-item">
                  <div className="detail-key">Reviewed By</div>
                  <div className="detail-val">{String(rec.reviewed_by_name)} · {new Date(String(rec.reviewed_at)).toLocaleString('en-GB')}</div>
                </div>
              )}
              {rec.reviewer_note && (
                <div className="detail-item" style={{ gridColumn: '1/-1' }}>
                  <div className="detail-key">Reviewer Note</div>
                  <div className="detail-val">{String(rec.reviewer_note)}</div>
                </div>
              )}
              {rec.edit_note && (
                <div className="detail-item" style={{ gridColumn: '1/-1' }}>
                  <div className="detail-key">Edit Note</div>
                  <div className="detail-val" style={{ color: 'var(--amber-400)' }}>✎ {String(rec.edit_note)}</div>
                </div>
              )}
            </div>
          </div>
        )}

        {tab === 'raw' && rawRow && (
          <div className="card">
            <div style={{ marginBottom: 12 }}>
              <StatusBadge status={String(rawRow.parse_status)} type="parse" />
              <span style={{ marginLeft: 10, fontSize: '0.78rem', color: 'var(--text-muted)' }}>Row #{String(rawRow.row_number)} from source file</span>
            </div>
            {(rawRow.parse_errors as string[]).map((e: string, i: number) => (
              <div key={i} className="alert alert-error" style={{ marginBottom: 6 }}>✕ {e}</div>
            ))}
            {(rawRow.parse_warnings as string[]).map((w: string, i: number) => (
              <div key={i} className="alert alert-warn" style={{ marginBottom: 6 }}>⚑ {w}</div>
            ))}
            <div style={{ overflow: 'auto', maxHeight: 400, background: 'var(--bg-card2)', borderRadius: 8, padding: 16 }}>
              <pre style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontFamily: 'JetBrains Mono, monospace', margin: 0 }}>
                {JSON.stringify(rawRow.raw_data, null, 2)}
              </pre>
            </div>
          </div>
        )}

        {tab === 'audit' && (
          <div className="card">
            {audit.length === 0 ? (
              <div className="empty-state" style={{ padding: 24 }}><div className="empty-text">No audit entries</div></div>
            ) : audit.map(log => (
              <div key={String(log.id)} style={{
                display: 'flex', gap: 14, padding: '12px 0',
                borderBottom: '1px solid var(--border)', alignItems: 'flex-start'
              }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', minWidth: 120, whiteSpace: 'nowrap' }}>
                  {new Date(String(log.timestamp)).toLocaleString('en-GB', { dateStyle: 'short', timeStyle: 'short' })}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                    <span className={`badge ${log.action === 'APPROVED' ? 'badge-dk-green' : log.action === 'REJECTED' ? 'badge-dk-red' : log.action === 'EDITED' ? 'badge-dk-amber' : 'badge-dk-gray'}`}>
                      {String(log.action_display)}
                    </span>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>by {String(log.user_name)}</span>
                  </div>
                  {log.note && <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>{String(log.note)}</div>}
                  {Object.keys(log.old_values as object).length > 0 && (
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4, fontFamily: 'monospace' }}>
                      before: {JSON.stringify(log.old_values)} → after: {JSON.stringify(log.new_values)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
