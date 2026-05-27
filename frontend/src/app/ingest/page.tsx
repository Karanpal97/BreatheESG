'use client';
import { useState, useRef, DragEvent } from 'react';
import AppShell from '@/components/AppShell';
import StatusBadge from '@/components/StatusBadge';
import { uploadFile } from '@/lib/api';
import { useRouter } from 'next/navigation';

const SOURCE_TYPES = [
  { value: 'SAP_FUEL', label: 'SAP — Fuel & Procurement', icon: '🏭',
    desc: 'Tab-delimited flat file exported from SAP SE16N / FAGLL03. German headers supported.',
    accept: '.txt,.xlsx,.xls,.csv' },
  { value: 'UTILITY_ELECTRICITY', label: 'Utility — Electricity', icon: '⚡',
    desc: 'Portal CSV export from utility provider (E.ON, British Gas for Business, etc.).',
    accept: '.csv,.xlsx' },
  { value: 'TRAVEL_CONCUR', label: 'Corporate Travel — Concur', icon: '✈',
    desc: 'Concur admin expense export CSV (SAE format). Handles flights, hotels, ground transport.',
    accept: '.csv,.xlsx' },
];

export default function IngestPage() {
  const [sourceType, setSourceType] = useState('SAP_FUEL');
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const selectedSource = SOURCE_TYPES.find(s => s.value === sourceType)!;

  const handleDrop = (e: DragEvent) => {
    e.preventDefault(); setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  };

  const handleSubmit = async () => {
    if (!file) { setError('Please select a file'); return; }
    setLoading(true); setError(''); setResult(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('source_type', sourceType);
      const res = await uploadFile(fd);
      setResult(res.data);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: string } } };
      setError(err.response?.data?.error || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <div className="topbar">
        <div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Data Ingestion</div>
          <div style={{ fontWeight: 700 }}>Upload New File</div>
        </div>
      </div>

      <div className="page-content" style={{ maxWidth: 800 }}>
        {/* Source type selector */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-title" style={{ marginBottom: 16 }}>1. Select data source type</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {SOURCE_TYPES.map(s => (
              <label key={s.value} style={{
                display: 'flex', alignItems: 'flex-start', gap: 14, padding: '14px 16px',
                borderRadius: 'var(--radius-sm)', cursor: 'pointer',
                border: `1px solid ${sourceType === s.value ? 'rgba(34,197,94,.4)' : 'var(--border-light)'}`,
                background: sourceType === s.value ? 'var(--accent-glow)' : 'var(--bg-card2)',
                transition: 'all 0.15s',
              }}>
                <input type="radio" name="source" value={s.value} checked={sourceType === s.value}
                  onChange={() => { setSourceType(s.value); setFile(null); setResult(null); }}
                  style={{ marginTop: 2, accentColor: 'var(--green-500)', width: 'auto' }} />
                <div style={{ fontSize: '1.3rem', lineHeight: 1 }}>{s.icon}</div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text)' }}>{s.label}</div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 3 }}>{s.desc}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Upload zone */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-title" style={{ marginBottom: 16 }}>2. Upload file</div>
          <div
            className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
          >
            <div className="upload-icon">{file ? '📄' : '☁'}</div>
            {file ? (
              <>
                <div style={{ fontWeight: 600, color: 'var(--text)', fontSize: '0.9rem' }}>{file.name}</div>
                <div className="upload-hint">{(file.size / 1024).toFixed(1)} KB · Click to change</div>
              </>
            ) : (
              <>
                <div className="upload-text">Drop your file here, or click to browse</div>
                <div className="upload-hint">Accepts: {selectedSource.accept}</div>
              </>
            )}
          </div>
          <input ref={fileRef} type="file" accept={selectedSource.accept}
            style={{ display: 'none' }} onChange={e => setFile(e.target.files?.[0] || null)} />
        </div>

        {error && <div className="alert alert-error">⚠ {error}</div>}

        {/* Submit */}
        {!result && (
          <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', padding: '12px' }}
            onClick={handleSubmit} disabled={loading || !file}>
            {loading
              ? <><span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> Processing file…</>
              : `⬆ Ingest ${selectedSource.label}`}
          </button>
        )}

        {/* Result */}
        {result && (
          <div className="card" style={{ borderColor: 'rgba(34,197,94,.3)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
              <span style={{ fontSize: '1.5rem' }}>✅</span>
              <div>
                <div style={{ fontWeight: 700, fontSize: '1rem' }}>Ingestion Complete</div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{String(result.original_filename)}</div>
              </div>
              <StatusBadge status={String(result.status)} type="job" />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
              {[
                { label: 'Total rows', val: result.row_count_total, color: 'var(--text)' },
                { label: 'OK', val: result.row_count_ok, color: 'var(--green-400)' },
                { label: 'Suspicious', val: result.row_count_suspicious, color: 'var(--amber-400)' },
                { label: 'Failed', val: result.row_count_failed, color: 'var(--red-400)' },
              ].map(s => (
                <div key={s.label} style={{ textAlign: 'center', padding: '12px', background: 'var(--bg-card2)', borderRadius: 8 }}>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: s.color }}>{String(s.val)}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>{s.label}</div>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn btn-primary" onClick={() => router.push(`/jobs/${result.id}`)}>
                View job details →
              </button>
              <button className="btn btn-secondary" onClick={() => router.push('/records?review_status=PENDING_REVIEW')}>
                Go to review queue
              </button>
              <button className="btn btn-ghost" onClick={() => { setResult(null); setFile(null); }}>
                Upload another
              </button>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
