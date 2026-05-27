'use client';
import { useEffect, useState } from 'react';
import AppShell from '@/components/AppShell';
import StatusBadge from '@/components/StatusBadge';
import { getJobs } from '@/lib/api';
import { useRouter } from 'next/navigation';

const SOURCE_LABELS: Record<string, string> = {
  SAP_FUEL: 'SAP Fuel', UTILITY_ELECTRICITY: 'Electricity', TRAVEL_CONCUR: 'Travel'
};

export default function JobsPage() {
  const [jobs, setJobs] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const router = useRouter();

  useEffect(() => {
    const params: Record<string, string> = {};
    if (filter) params.source_type = filter;
    getJobs(params).then(r => setJobs(r.data)).finally(() => setLoading(false));
  }, [filter]);

  return (
    <AppShell>
      <div className="topbar">
        <div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Data Ingestion</div>
          <div style={{ fontWeight: 700 }}>Ingestion Jobs</div>
        </div>
        <button className="btn btn-primary btn-sm" onClick={() => router.push('/ingest')}>
          ⬆ Upload file
        </button>
      </div>

      <div className="page-content">
        <div className="filters-bar">
          <select className="filter-select" value={filter} onChange={e => setFilter(e.target.value)}>
            <option value="">All sources</option>
            <option value="SAP_FUEL">SAP Fuel</option>
            <option value="UTILITY_ELECTRICITY">Electricity</option>
            <option value="TRAVEL_CONCUR">Travel</option>
          </select>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
            {jobs.length} job{jobs.length !== 1 ? 's' : ''}
          </span>
        </div>

        {loading ? (
          <div className="loading-spinner"><div className="spinner" /><span>Loading jobs…</span></div>
        ) : jobs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">⊞</div>
            <div className="empty-text">No jobs yet — upload your first file</div>
            <button className="btn btn-primary btn-sm" onClick={() => router.push('/ingest')}>Upload now</button>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>File</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Total</th>
                  <th>OK</th>
                  <th>⚑ Suspicious</th>
                  <th>✕ Failed</th>
                  <th>Uploaded</th>
                  <th>By</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map(job => (
                  <tr key={String(job.id)} onClick={() => router.push(`/jobs/${job.id}`)}>
                    <td className="td-primary" style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      📄 {String(job.original_filename)}
                    </td>
                    <td>{SOURCE_LABELS[String(job.source_type)] || String(job.source_type)}</td>
                    <td><StatusBadge status={String(job.status)} type="job" /></td>
                    <td className="td-mono">{String(job.row_count_total)}</td>
                    <td className="td-mono" style={{ color: 'var(--green-400)' }}>{String(job.row_count_ok)}</td>
                    <td className="td-mono" style={{ color: 'var(--amber-400)' }}>{String(job.row_count_suspicious)}</td>
                    <td className="td-mono" style={{ color: 'var(--red-400)' }}>{String(job.row_count_failed)}</td>
                    <td style={{ fontSize: '0.78rem', whiteSpace: 'nowrap' }}>
                      {new Date(String(job.uploaded_at)).toLocaleString('en-GB', { dateStyle: 'short', timeStyle: 'short' })}
                    </td>
                    <td style={{ fontSize: '0.78rem' }}>{String(job.uploaded_by_name || '—')}</td>
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
