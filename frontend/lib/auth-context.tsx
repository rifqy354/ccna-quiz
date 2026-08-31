'use client';
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User { id: number; email: string; name: string; }

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedToken = localStorage.getItem('access_token');
    const savedUser = localStorage.getItem('user');
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
      fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/auth/me`, {
        headers: { Authorization: `Bearer ${savedToken}` },
      }).then(r => {
        if (!r.ok) throw new Error('Invalid token');
        return r.json();
      }).then(u => setUser(u)).catch(() => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        setToken(null); setUser(null);
      });
    }
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Login failed'); }
    const data = await r.json();
    const me = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/auth/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` },
    }).then(r2 => r2.json());
    setToken(data.access_token); setUser(me);
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('user', JSON.stringify(me));
  };

  const register = async (email: string, password: string, name: string) => {
    await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name }),
    });
    await login(email, password);
  };

  const logout = () => {
    setUser(null); setToken(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  };

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
