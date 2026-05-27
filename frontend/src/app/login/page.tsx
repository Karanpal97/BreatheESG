'use client';
import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      await login(email, password);
      router.push('/dashboard');
    } catch {
      setError('Invalid email or password. Try admin@acme.com / admin123');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <div className="login-logo-icon">🌿</div>
          <div>
            <div className="login-title">Breathe ESG</div>
            <div className="login-sub">Emissions Data Platform</div>
          </div>
        </div>

        {error && (
          <div className="alert alert-error" style={{ marginBottom: 20 }}>
            ⚠ {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email address</label>
            <input
              id="email" type="email" required
              value={email} onChange={e => setEmail(e.target.value)}
              placeholder="analyst@acme.com"
              autoComplete="email"
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password" type="password" required
              value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </div>
          <button className="btn btn-primary login-btn" type="submit" disabled={loading}>
            {loading ? <><span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> Signing in…</> : 'Sign in →'}
          </button>
        </form>

        <div style={{ marginTop: 24, padding: '12px 16px', background: 'var(--bg-card2)', 
                      borderRadius: 8, fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.7 }}>
          <strong style={{ color: 'var(--text-dim)' }}>Demo credentials</strong><br />
          Admin: admin@acme.com / admin123<br />
          Analyst: analyst@acme.com / analyst123
        </div>
      </div>
    </div>
  );
}
