'use client';
import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import Link from 'next/link';

export default function RegisterPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const pending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const { register } = useAuth();
  const router = useRouter();

  const handle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pending.current) return;
    pending.current = true; setBusy(true); setError('');
    try {
      await register(email, password, name);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally { pending.current = false; setBusy(false); }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="card" style={{ width: '100%', maxWidth: '400px', margin: '1rem' }}>
        <h1 style={{ marginBottom: '1.5rem' }}>Create Account</h1>
        <form onSubmit={handle} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {error && <p style={{ color: '#dc2626', background: '#fee2e2', padding: '0.75rem', borderRadius: '6px' }}>{error}</p>}
          <label>Name<input type="text" value={name} onChange={e => setName(e.target.value)} required /></label>
          <label>Email<input type="email" value={email} onChange={e => setEmail(e.target.value)} required /></label>
          <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={8} /></label>
          <button disabled={busy} type="submit" style={{ marginTop: '0.5rem' }}>Create Account</button>
        </form>
        <p style={{ marginTop: '1rem', textAlign: 'center', fontSize: '0.875rem' }}>
          Have an account? <Link href="/login">Login</Link>
        </p>
      </div>
    </div>
  );
}
