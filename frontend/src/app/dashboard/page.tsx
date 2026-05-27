'use client';
import { useEffect, useState } from 'react';
import AppShell from '@/components/AppShell';
import StatusBadge from '@/components/StatusBadge';
import { getDashboard } from '@/lib/api';
import { useRouter } from 'next/navigation';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell
} from 'recharts';

interface Summary {
  total_co2e_kg: number; scope_1_co2e_kg: number;
  scope_2_co2e_kg: number; scope_3_co2e_kg: number;
  pending_review_count: number; flagged_count: number;
  approved_count: number; rejected_count: number;
  total_records: number; jobs_done: number; jobs_failed: number;
  by_source: { source_type: string; co2e_kg: number; count: number }[];
  recent_jobs: Record<string, unknown>[];
}

const SOURCE_LABELS: Record<string, string> = {
  SAP_FUEL: 'SAP Fuel', UTILITY_ELECTRICITY: 'Electricity', TRAVEL_CONCUR: 'Travel'
};
const SOURCE_COLORS: Record<string, string> = {
  SAP_FUEL: '#ef4444', UTILITY_ELECTRICITY: '#3b82f6', TRAVEL_CONCUR: '#8b5cf6'
};

function fmt(n: number) {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}t`;
  return n.toFixed(1);
}

export default function DashboardPage() {
  const [data, setData] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    getDashboard().then(r => setData(r.data)).finally(() => setLoading(false));
  }, []);

  const scopeData = data ? [
    { name: 'Scope 1\nDirect', kg: data.scope_1_co2e_kg, color: '#ef4444' },
    { name: 'Scope 2\nElectricity', kg: data.scope_2_co2e_kg, color: '#3b82f6' },
    { name: 'Scope 3\nValue chain', kg: data.scope_3_co2e_kg, color: '#8b5cf6' },
  ] : [];

  return (
    <AppShell>
      <div className="topbar">
        <div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Overview</div>
          <div style={{ fontWeight: 700, fontSize: '1rem' }}>Emissions Dashboard</div>
        </div>
        <span className="badge badge-dk-green">● Live</span>
      </div>

      <div className="page-content">
        {loading ? (
          <div className="loading-spinner"><div className="spinner" /><span>Loading…</span></div>
        ) : !data ? (
          <div className="empty-state"><div className="empty-icon">⚠</div><div className="empty-text">Could not load dashboard</div></div>
        ) : (
          <>
            {/* KPI row */}
            <div className="stat-grid">
              <div className="stat-card" style={{ '--accent-color': '#22c55e' } as React.CSSProperties}>
                <div className="stat-label">Total CO₂e</div>
                <div className="stat-value">{fmt(data.total_co2e_kg)}</div>
                <div className="stat-unit">kg CO₂e across all sources</div>
                <div className="stat-icon">🌍</div>
              </div>
              <div className="stat-card" style={{ '--accent-color': '#ef4444' } as React.CSSProperties}>
                <div className="stat-label">Scope 1 (Direct)</div>
                <div className="stat-value">{fmt(data.scope_1_co2e_kg)}</div>
                <div className="stat-unit">kg CO₂e — fuel combustion</div>
                <div className="stat-icon">🔥</div>
              </div>
              <div className="stat-card" style={{ '--accent-color': '#3b82f6' } as React.CSSProperties}>
                <div className="stat-label">Scope 2 (Energy)</div>
                <div className="stat-value">{fmt(data.scope_2_co2e_kg)}</div>
                <div className="stat-unit">kg CO₂e — purchased electricity</div>
                <div className="stat-icon">⚡</div>
              </div>
              <div className="stat-card" style={{ '--accent-color': '#8b5cf6' } as React.CSSProperties}>
                <div className="stat-label">Scope 3 (Value Chain)</div>
                <div className="stat-value">{fmt(data.scope_3_co2e_kg)}</div>
                <div className="stat-unit">kg CO₂e — business travel</div>
                <div className="stat-icon">✈</div>
              </div>
            </div>

            {/* Review status + chart row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
              {/* Review queue */}
              <div className="card">
                <div className="card-header">
                  <div><div className="card-title">Review Queue</div>
                    <div className="card-subtitle">{data.total_records} total records</div></div>
                  <button className="btn btn-primary btn-sm" onClick={() => router.push('/records')}>
                    Review →
                  </button>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {[
                    { label: 'Pending Review', count: data.pending_review_count, cls: 'badge-dk-amber' },
                    { label: 'Flagged', count: data.flagged_count, cls: 'badge-dk-red' },
                    { label: 'Approved', count: data.approved_count, cls: 'badge-dk-green' },
                    { label: 'Rejected', count: data.rejected_count, cls: 'badge-dk-gray' },
                  ].map(r => (
                    <div key={r.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.82rem', color: 'var(--text-dim)' }}>{r.label}</span>
                      <span className={`badge ${r.cls}`}>{r.count}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Scope breakdown chart */}
              <div className="card">
                <div className="card-header">
                  <div><div className="card-title">Emissions by Scope</div>
                    <div className="card-subtitle">kg CO₂e breakdown</div></div>
                </div>
                <ResponsiveContainer width="100%" height={140}>
                  <BarChart data={scopeData} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Tooltip
                      contentStyle={{ background: '#111827', border: '1px solid #1e2d3d', borderRadius: 8, fontSize: 12 }}
                      formatter={(v: number) => [`${v.toFixed(1)} kg CO₂e`, '']}
                    />
                    <Bar dataKey="kg" radius={[4, 4, 0, 0]}>
                      {scopeData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* By source + recent jobs */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="card">
                <div className="card-header">
                  <div className="card-title">Emissions by Source</div>
                </div>
                {data.by_source.length === 0 ? (
                  <div className="empty-state" style={{ padding: 20 }}>
                    <div className="empty-text">No data yet — upload files to start</div>
                  </div>
                ) : data.by_source.map(s => (
                  <div key={s.source_type} style={{ marginBottom: 14 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5, fontSize: '0.8rem' }}>
                      <span style={{ color: 'var(--text-dim)' }}>{SOURCE_LABELS[s.source_type] || s.source_type}</span>
                      <span style={{ color: 'var(--text)', fontWeight: 600 }}>{fmt(s.co2e_kg)} kg</span>
                    </div>
                    <div className="progress-bar">
                      <div className="progress-fill" style={{
                        width: `${Math.min(100, (s.co2e_kg / data.total_co2e_kg) * 100)}%`,
                        background: SOURCE_COLORS[s.source_type] || 'var(--green-500)',
                      }} />
                    </div>
                  </div>
                ))}
              </div>

              <div className="card">
                <div className="card-header">
                  <div><div className="card-title">Recent Jobs</div>
                    <div className="card-subtitle">{data.jobs_done} completed · {data.jobs_failed} failed</div></div>
                  <button className="btn btn-secondary btn-sm" onClick={() => router.push('/jobs')}>
                    All jobs
                  </button>
                </div>
                {(data.recent_jobs as Record<string, unknown>[]).length === 0 ? (
                  <div className="empty-state" style={{ padding: 20 }}>
                    <div className="empty-text">No ingestion jobs yet</div>
                  </div>
                ) : (data.recent_jobs as Record<string, unknown>[]).map((job) => (
                  <div key={String(job.id)} style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '8px 0', borderBottom: '1px solid var(--border)', cursor: 'pointer'
                  }} onClick={() => router.push(`/jobs/${job.id}`)}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--text)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {String(job.original_filename)}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {String(job.source_type_display)} · {String(job.row_count_total)} rows
                      </div>
                    </div>
                    <StatusBadge status={String(job.status)} type="job" />
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
