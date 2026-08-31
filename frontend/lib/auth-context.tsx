'use client';
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from './api';

interface User { id: number; email: string; name: string; }
interface AuthContextType {
  user: User | null; token: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void; loading: boolean;
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
      setToken(savedToken); setUser(JSON.parse(savedUser));
      api.auth.me(savedToken).catch(() => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        setToken(null); setUser(null);
      });
    }
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const { access_token } = await api.auth.login({ email, password });
    const userData = await api.auth.me(access_token);
    setToken(access_token); setUser(userData);
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('user', JSON.stringify(userData));
  };

  const register = async (email: string, password: string, name: string) => {
    await api.auth.register({ email, password, name });
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
