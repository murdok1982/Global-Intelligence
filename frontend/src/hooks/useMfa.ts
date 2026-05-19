'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type {
  MfaEnrollResponse,
  MfaStatus,
  LoginResponseTokens,
} from '@/lib/api/types';

// ---------------------------------------------------------------------------
// Status
// ---------------------------------------------------------------------------

export function useMfaStatus() {
  return useQuery<MfaStatus>({
    queryKey: ['mfa', 'status'],
    queryFn: async () => {
      const { data } = await apiClient.get<MfaStatus>('/auth/mfa/status');
      return data;
    },
    staleTime: 60 * 1000,
    retry: false,
  });
}

// ---------------------------------------------------------------------------
// Enrollment
// ---------------------------------------------------------------------------

export function useEnrollMfa() {
  return useMutation<MfaEnrollResponse, Error, void>({
    mutationFn: async () => {
      const { data } = await apiClient.post<MfaEnrollResponse>(
        '/auth/mfa/enroll/start',
        {},
      );
      return data;
    },
  });
}

export function useVerifyEnrollment() {
  const queryClient = useQueryClient();
  return useMutation<{ verified: boolean }, Error, { code: string }>({
    mutationFn: async ({ code }) => {
      const { data } = await apiClient.post<{ verified: boolean }>(
        '/auth/mfa/enroll/verify',
        { code },
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mfa', 'status'] });
      queryClient.invalidateQueries({ queryKey: ['me'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Login challenge
// ---------------------------------------------------------------------------

export interface MfaChallengeRequest {
  challenge_token: string;
  /** Código TOTP de 6 dígitos. */
  code?: string;
  /** Código de recuperación (alternativo). */
  recovery_code?: string;
}

export function useMfaChallenge() {
  return useMutation<LoginResponseTokens, Error, MfaChallengeRequest>({
    mutationFn: async (payload) => {
      const { data } = await apiClient.post<LoginResponseTokens>(
        '/auth/mfa/verify',
        payload,
      );
      return data;
    },
  });
}

// ---------------------------------------------------------------------------
// Disable
// ---------------------------------------------------------------------------

export function useDisableMfa() {
  const queryClient = useQueryClient();
  return useMutation<{ disabled: boolean }, Error, { code: string }>({
    mutationFn: async ({ code }) => {
      const { data } = await apiClient.post<{ disabled: boolean }>(
        '/auth/mfa/disable',
        { code },
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mfa', 'status'] });
      queryClient.invalidateQueries({ queryKey: ['me'] });
    },
  });
}
