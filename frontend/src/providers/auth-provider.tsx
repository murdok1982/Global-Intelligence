'use client';

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
} from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import apiClient, {
  setInMemoryAccessToken,
  clearInMemoryAccessToken,
} from '@/lib/api-client';
import type { User } from '@/lib/types';

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  getAccessToken: () => string | null;
  login: (accessToken: string, refreshToken: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  getAccessToken: () => null,
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  // Access token lives only in memory — never in localStorage or readable cookies.
  // This eliminates XSS token theft via storage APIs.
  const accessTokenRef = useRef<string | null>(null);
  const router = useRouter();

  const getAccessToken = useCallback(() => accessTokenRef.current, []);

  const fetchMe = useCallback(async () => {
    // Only attempt if we have an in-memory token OR a refresh cookie to hydrate from.
    const hasToken = accessTokenRef.current !== null;
    const hasRefreshCookie = !!Cookies.get('refresh_token');
    if (!hasToken && !hasRefreshCookie) {
      setIsLoading(false);
      return;
    }
    try {
      const { data } = await apiClient.get<User>('/auth/me');
      setUser(data);
    } catch {
      setUser(null);
      accessTokenRef.current = null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  const login = useCallback(
    (accessToken: string, refreshToken: string) => {
      // Access token: memory only — never written to any browser storage.
      accessTokenRef.current = accessToken;
      setInMemoryAccessToken(accessToken);
      // Refresh token: HttpOnly cannot be set from JS. We use js-cookie with
      // SameSite=Strict and the narrowest possible path so it is only sent to
      // the refresh endpoint. Mark secure=true so it is HTTPS-only in production.
      Cookies.set('refresh_token', refreshToken, {
        expires: 7,
        path: '/api/v1/auth/refresh',
        sameSite: 'strict',
        secure: process.env.NODE_ENV === 'production',
      });
      // Route-guard cookie: NOT HttpOnly (Next.js middleware reads it in the
      // Edge runtime). Contains no secret — its sole purpose is to let the
      // middleware know a session exists so it can redirect unauthenticated
      // users. The actual bearer token used for API calls comes from memory.
      Cookies.set('session_present', '1', {
        expires: 7,
        sameSite: 'strict',
        secure: process.env.NODE_ENV === 'production',
      });
      fetchMe();
    },
    [fetchMe]
  );

  const logout = useCallback(() => {
    accessTokenRef.current = null;
    clearInMemoryAccessToken();
    Cookies.remove('refresh_token', { path: '/api/v1/auth/refresh' });
    Cookies.remove('session_present');
    setUser(null);
    router.push('/auth');
  }, [router]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        getAccessToken,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
