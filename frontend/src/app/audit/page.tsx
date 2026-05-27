'use client';
import { useEffect, useState } from 'react';
import AppShell from '@/components/AppShell';
import { getRecords } from '@/lib/api';

export default function AuditPage() {
  const [records, setRecords] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRecords({ review_status: 'APPROVED' }).then(r => setRecords(r.data)).finally(() => setLoading(false));
  }, []);

  const totalCo2e = records.reduce((sum, r) => sum + Number(r.co2e_kg), 0);
  const byScope = records.reduce((acc, r) => {
    const s = String(r.scope);
    acc[s] = (acc[s] || 0) + Number(r.co2e_kg);
    return acc;
  }, {} as Record<string, number>);

  return (
    <AppShell>
      <div className="topbar">
        <div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Read-only</div>
          <div style={{ fontWeight: 700 }}>Audit Export — Approved Records</div>
        </div>
        <span className="badge badge-dk-green">🔒 Locked records only</span>
      </div>

      <div className="page-content">
        {/* Summary strip */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 24 }}>
          {[
            { label: 'Approved Records', val: records.length, color: 'var(--green-400)' },
            { label: 'Total CO₂e', val: `${totalCo2e.toFixed(1)} kg`, color: 'var(--text)' },
            { label: 'Scope 1', val: `${(byScope.SCOPE_1 || 0).toFixed(1)} kg`, color: 'var(--red-400)' },
            { label: 'Scope 2', val: `${(byScope.SCOPE_2 || 0).toFixed(1)} kg`, color: 'var(--blue-400)' },
          ].map(s => (
            <div key={s.label} className="card card-sm" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.3rem', fontWeight: 800, color: s.color }}>{s.val}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 3 }}>{s.label}</div>
            </div>
          ))}
        </div>

        <div className="alert alert-warn" style={{ marginBottom: 20 }}>
          ⚑ This view shows only locked (approved) records. These are the records that would be exported to your auditor.
          Records pending review or flagged are excluded.
        </div>

        {loading ? (
          <div className="loading-spinner"><div className="spinner" /></div>
        ) : records.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🔒</div>
            <div className="empty-text">No approved records yet — go to Review to approve records</div>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Description</th>
                  <th>Scope</th>
                  <th>Source</th>
                  <th>Activity</th>
                  <th>Emission Factor</th>
                  <th>CO₂e (kg)</th>
                  <th>Period Start</th>
                  <th>Period End</th>
                  <th>EF Source</th>
                  <th>Approved By</th>
                  <th>Approved At</th>
                </tr>
              </thead>
              <tbody>
                {records.map(r => (
                  <tr key={String(r.id)} style={{ cursor: 'default' }}>
                    <td className="td-primary" style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {String(r.activity_description)}
                    </td>
                    <td><span className="badge badge-dk-gray">{String(r.scope)}</span></td>
                    <td style={{ fontSize: '0.78rem' }}>{String(r.source_type)}</td>
                    <td className="td-mono">{Number(r.activity_value).toFixed(4)} {String(r.activity_unit)}</td>
                    <td className="td-mono">{Number(r.emission_factor).toFixed(5)}</td>
                    <td className="td-mono" style={{ color: 'var(--green-400)', fontWeight: 600 }}>
                      {Number(r.co2e_kg).toFixed(4)}
                    </td>
                    <td className="td-mono">{String(r.data_period_start || '—')}</td>
                    <td className="td-mono">{String(r.data_period_end || '—')}</td>
                    <td style={{ fontSize: '0.75rem' }}>{String(r.emission_factor_source)}</td>
                    <td style={{ fontSize: '0.78rem' }}>{String(r.reviewed_by_name || '—')}</td>
                    <td style={{ fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                      {r.reviewed_at ? new Date(String(r.reviewed_at)).toLocaleString('en-GB', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
