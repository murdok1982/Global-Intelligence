'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import apiClient, { setInMemoryAccessToken } from '@/lib/api-client';
import type {
  LoginRequest,
  RegisterRequest,
  RegisterResponse,
} from '@/lib/types';
import {
  isMfaRequired,
  type LoginResponse,
  type LoginResponseTokens,
} from '@/lib/api/types';

// Re-export del hook canónico — fuente de verdad en `useCurrentUser.ts`.
export { useCurrentUser } from './useCurrentUser';

/** Clave de sessionStorage para el challenge_token entre /auth y /auth/mfa. */
export const MFA_CHALLENGE_STORAGE_KEY = 'mfa_challenge_token';
export const MFA_CHALLENGE_EXPIRES_KEY = 'mfa_challenge_expires_at';

/**
 * Persiste tokens emitidos por el backend tras una autenticación exitosa
 * (login directo o login + MFA). Mantiene el access token en memoria + cookie
 * sentinel, y el refresh token en cookie estricta.
 */
export function persistAuthTokens(tokens: LoginResponseTokens): void {
  setInMemoryAccessToken(tokens.access_token);
  // Cookie sentinel (no contiene el token) para el middleware.
  Cookies.set('session_present', '1', {
    expires: 1, // 1 día — se renueva con refresh
    sameSite: 'strict',
    secure: typeof window !== 'undefined' && window.location.protocol === 'https:',
  });
  // refresh_token en cookie estricta — limitada al endpoint de refresh.
  Cookies.set('refresh_token', tokens.refresh_token, {
    expires: 7,
    sameSite: 'strict',
    secure: typeof window !== 'undefined' && window.location.protocol === 'https:',
    path: '/api/v1/auth/refresh',
  });
}

export function useLogin() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation<LoginResponse, Error, LoginRequest>({
    mutationFn: async (credentials) => {
      const { data } = await apiClient.post<LoginResponse>(
        '/auth/login',
        credentials,
      );
      return data;
    },
    onSuccess: (data) => {
      if (isMfaRequired(data)) {
        // Guarda el challenge token en sessionStorage y redirige al desafío.
        if (typeof window !== 'undefined') {
          const expiresAt = Date.now() + data.expires_in * 1000;
          sessionStorage.setItem(MFA_CHALLENGE_STORAGE_KEY, data.challenge_token);
          sessionStorage.setItem(MFA_CHALLENGE_EXPIRES_KEY, String(expiresAt));
        }
        router.push('/auth/mfa');
        return;
      }
      persistAuthTokens(data);
      queryClient.invalidateQueries({ queryKey: ['me'] });
      router.push('/dashboard');
    },
  });
}

export function useRegister() {
  const router = useRouter();

  return useMutation<RegisterResponse, Error, RegisterRequest>({
    mutationFn: async (payload) => {
      const { data } = await apiClient.post<RegisterResponse>(
        '/auth/register',
        payload
      );
      return data;
    },
    onSuccess: () => {
      router.push('/auth?registered=true');
    },
  });
}

export function useLogout() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return () => {
    setInMemoryAccessToken(null);
    Cookies.remove('session_present');
    Cookies.remove('refresh_token', { path: '/api/v1/auth/refresh' });
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem(MFA_CHALLENGE_STORAGE_KEY);
      sessionStorage.removeItem(MFA_CHALLENGE_EXPIRES_KEY);
    }
    queryClient.clear();
    router.push('/auth');
  };
}
