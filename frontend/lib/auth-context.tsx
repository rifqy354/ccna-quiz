'use client';
import { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { apiFetch, setRefreshHandler } from './api';
interface User { id: number; email: string; name: string; }
interface Tokens { access_token: string; refresh_token: string; }
interface AuthContextType {
 user: User | null; token: string | null; loading: boolean;
 login: (email: string, password: string) => Promise<void>;
 register: (email: string, password: string, name: string) => Promise<void>;
 logout: () => void;
}
const AuthContext = createContext<AuthContextType | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
 const [user,setUser] = useState<User | null>(null);
 const [token,setToken] = useState<string | null>(null);
 const [loading,setLoading] = useState(true);
 const pathname = usePathname(); const router = useRouter();
 const generation = useRef(0);
 const logout = () => {
   generation.current++;
   setUser(null); setToken(null); setLoading(false);
   ['access_token','refresh_token','user'].forEach(k => localStorage.removeItem(k));
 };
 const saveTokens = (data: Tokens) => {
   localStorage.setItem('access_token',data.access_token);
   localStorage.setItem('refresh_token',data.refresh_token);
   setToken(data.access_token);
 };
 useEffect(() => {
   let pending: Promise<string | null> | null = null;
   setRefreshHandler(() => {
     if (pending) return pending;
     const current = generation.current;
     pending = (async () => {
       const refresh_token = localStorage.getItem('refresh_token');
       if (!refresh_token) { logout(); return null; }
       try { const data = await apiFetch<Tokens>('/api/auth/refresh',undefined,{refresh_token}); if (current !== generation.current) return null; saveTokens(data); return data.access_token; }
       catch { if (current === generation.current) logout(); return null; }
       finally { pending = null; }
     })();
     return pending;
   });
   // The server validates identity; stale or corrupted cached user data is ignored.
   const current = generation.current;
   const saved = localStorage.getItem('access_token');
   if (!saved) { setLoading(false); return () => setRefreshHandler(null); }
   apiFetch<User>('/api/auth/me',saved).then(me => {
     if (current !== generation.current) return;
     setUser(me); setToken(localStorage.getItem('access_token'));
     localStorage.setItem('user',JSON.stringify(me));
   }).catch(() => { if (current === generation.current) logout(); }).finally(() => setLoading(false));
   return () => { generation.current++; setRefreshHandler(null); };
 }, []);
 useEffect(() => {
   if (!loading && !user && !pathname.startsWith('/portfolio') && pathname !== '/' && pathname !== '/login' && pathname !== '/register') router.replace('/login');
 },[loading,user,pathname,router]);
 const login = async (email: string,password: string) => {
   const data = await apiFetch<Tokens>('/api/auth/login',undefined,{email,password});
   const me = await apiFetch<User>('/api/auth/me',data.access_token);
   saveTokens(data); setUser(me); localStorage.setItem('user',JSON.stringify(me));
 };
 const register = async (email: string,password: string,name: string) => {
   await apiFetch<User>('/api/auth/register',undefined,{email,password,name});
   await login(email,password);
 };
 return <AuthContext.Provider value={{user,token,loading,login,register,logout}}>{children}</AuthContext.Provider>;
}
export function useAuth() { const ctx = useContext(AuthContext); if (!ctx) throw new Error('useAuth must be used within AuthProvider'); return ctx; }
