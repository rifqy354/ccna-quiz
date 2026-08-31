'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading) {
      if (user) router.push('/dashboard');
      else router.push('/login');
    }
  }, [user, loading, router]);
  return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
    <p style={{ color: '#6b7280' }}>Loading...</p>
  </div>;
}
