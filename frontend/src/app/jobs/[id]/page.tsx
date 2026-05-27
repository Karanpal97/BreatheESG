'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import AppShell from '@/components/AppShell';
import StatusBadge from '@/components/StatusBadge';
import { getJob, getJobRows } from '@/lib/api';

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [job, setJob] = useState<Record<string, unknown> | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [rowFilter, setRowFilter] = useState('');
  const [loadingJob, setLoadingJob] = useState(true);
  const [loadingRows, setLoadingRows] = useState(true);

  useEffect(() => {
    getJob(id).then(r => setJob(r.data)).finally(() => setLoadingJob(false));
  }, [id]);

  useEffect(() => {
    const params: Record<string, string> = {};
    if (rowFilter) params.status = rowFilter;
    setLoadingRows(true);
    getJobRows(id, params).then(r => setRows(r.data)).finally(() => setLoadingRows(false));
  }, [id, rowFilter]);

  return (
    <AppShell>
      <div className="topbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-ghost btn-sm" onClick={() => router.push('/jobs')}>← Jobs</button>
          <div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Job Detail</div>
            <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>
              {loadingJob ? '…' : String(job?.original_filename || '')}
            </div>
          </div>
        </div>
        {job && <StatusBadge status={String(job.status)} type="job" />}
      </div>

      <div className="page-content">
        {/* Job summary */}
        {!loadingJob && job && (
          <div className="card" style={{ marginBottom: 20 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 16 }}>
              {[
                { label: 'Source Type', val: String(job.source_type_display) },
                { label: 'Uploaded By', val: String(job.uploaded_by_name || '—') },
                { label: 'Uploaded At', val: new Date(String(job.uploaded_at)).toLocaleString('en-GB') },
                { label: 'Parser Version', val: String(job.parser_version) },
                { label: 'Total Rows', val: String(job.row_count_total), color: 'var(--text)' },
                { label: 'OK', val: String(job.row_count_ok), color: 'var(--green-400)' },
                { label: 'Suspicious', val: String(job.row_count_suspicious), color: 'var(--amber-400)' },
                { label: 'Failed', val: String(job.row_count_failed), color: 'var(--red-400)' },
              ].map(item => (
                <div key={item.label}>
                  <div className="detail-key">{item.label}</div>
                  <div className="detail-val" style={{ color: item.color }}>{item.val}</div>
                </div>
              ))}
            </div>
            {job.status === 'DONE' && (
              <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                <button className="btn btn-primary btn-sm" onClick={() => router.push(`/records?job=${id}`)}>
                  View emission records from this job →
                </button>
              </div>
            )}
          </div>
        )}

        {/* Rows table */}
        <div className="card-header" style={{ marginBottom: 12 }}>
          <div style={{ fontWeight: 600 }}>Raw Rows</div>
          <div className="tabs" style={{ margin: 0 }}>
            {['', 'OK', 'SUSPICIOUS', 'FAILED'].map(s => (
              <button key={s} className={`tab ${rowFilter === s ? 'active' : ''}`}
                onClick={() => setRowFilter(s)}>
                {s || 'All'}
              </button>
            ))}
          </div>
        </div>

        {loadingRows ? (
          <div className="loading-spinner"><div className="spinner" /></div>
        ) : rows.length === 0 ? (
          <div className="empty-state"><div className="empty-text">No rows match this filter</div></div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Status</th>
                  <th>Errors / Warnings</th>
                  <th>Raw Data (preview)</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(row => (
                  <tr key={String(row.id)} style={{ cursor: 'default' }}>
                    <td className="td-mono" style={{ width: 60 }}>{String(row.row_number)}</td>
                    <td style={{ width: 120 }}><StatusBadge status={String(row.parse_status)} type="parse" /></td>
                    <td style={{ maxWidth: 300 }}>
                      {(row.parse_errors as string[]).map((e, i) => (
                        <div key={i} style={{ fontSize: '0.75rem', color: 'var(--red-400)', marginBottom: 2 }}>✕ {e}</div>
                      ))}
                      {(row.parse_warnings as string[]).map((w, i) => (
                        <div key={i} style={{ fontSize: '0.75rem', color: 'var(--amber-400)', marginBottom: 2 }}>⚑ {w}</div>
                      ))}
                    </td>
                    <td style={{ maxWidth: 400 }}>
                      <pre style={{ fontSize: '0.7rem', color: 'var(--text-muted)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'pre',
                        maxHeight: 60, margin: 0 }}>
                        {JSON.stringify(row.raw_data, null, 0).slice(0, 300)}
                      </pre>
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
