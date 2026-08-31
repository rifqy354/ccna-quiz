'use client';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';

export default function NavBar() {
  const { user, logout } = useAuth();
  if (!user) return null;
  return (
    <nav style={{ padding: '0.75rem 1.5rem', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', gap: '1.5rem', background: 'white', position: 'sticky', top: 0, zIndex: 10 }}>
      <Link href="/dashboard" style={{ fontWeight: 700, color: '#111827', fontSize: '1.1rem' }}>CCNA Quiz</Link>
      <Link href="/domains" style={{ fontSize: '0.9rem', color: '#6b7280' }}>Domains</Link>
      <Link href="/stats" style={{ fontSize: '0.9rem', color: '#6b7280' }}>Stats</Link>
      <div style={{ marginLeft: 'auto', display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>{user.name}</span>
        <button onClick={logout} style={{ padding: '0.25rem 0.75rem', fontSize: '0.875rem', background: '#6b7280' }}>Logout</button>
      </div>
    </nav>
  );
}
