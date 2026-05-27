'use client';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useState, useEffect } from 'react';
import { getDashboard } from '@/lib/api';

interface NavItem {
  label: string; href: string; icon: string; badge?: number;
}

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    getDashboard().then(r => {
      setPendingCount((r.data.pending_review_count || 0) + (r.data.flagged_count || 0));
    }).catch(() => {});
  }, [pathname]);

  const navItems: NavItem[] = [
    { label: 'Dashboard', href: '/dashboard', icon: '◈' },
    { label: 'Upload Data', href: '/ingest', icon: '⬆' },
    { label: 'Ingestion Jobs', href: '/jobs', icon: '⊞' },
    { label: 'Review Records', href: '/records', icon: '✓', badge: pendingCount || undefined },
    { label: 'Audit Trail', href: '/audit', icon: '⋮' },
  ];

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  const initials = user
    ? `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase() || user.email[0].toUpperCase()
    : '?';

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-mark">
          <div className="logo-icon">🌿</div>
          <div>
            <div className="logo-text">Breathe ESG</div>
            <div className="logo-sub">{user?.company_name || 'Loading…'}</div>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-label">Platform</div>
        {navItems.map(item => (
          <button
            key={item.href}
            className={`nav-item ${pathname.startsWith(item.href) ? 'active' : ''}`}
            onClick={() => router.push(item.href)}
          >
            <span style={{ fontSize: '1rem', minWidth: 18 }}>{item.icon}</span>
            <span style={{ flex: 1 }}>{item.label}</span>
            {item.badge ? <span className="nav-badge">{item.badge}</span> : null}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="user-chip">
          <div className="user-avatar">{initials}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="user-name" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.first_name} {user?.last_name}
            </div>
            <div className="user-role">{user?.role}</div>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={handleLogout} title="Sign out"
            style={{ padding: '4px 8px', fontSize: '0.8rem' }}>
            ↩
          </button>
        </div>
      </div>
    </aside>
  );
}
