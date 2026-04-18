'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import apiClient from '@/lib/api-client';
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  User,
} from '@/lib/types';

export function useLogin() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation<LoginResponse, Error, LoginRequest>({
    mutationFn: async (credentials) => {
      const { data } = await apiClient.post<LoginResponse>(
        '/auth/login',
        credentials
      );
      return data;
    },
    onSuccess: (data) => {
      localStorage.setItem('access_token', data.access_token);
      // access_token in cookie for middleware (15 min)
      Cookies.set('access_token', data.access_token, { expires: 1 / 96 });
      // refresh_token in cookie only
      Cookies.set('refresh_token', data.refresh_token, { expires: 7 });
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

export function useCurrentUser() {
  return useQuery<User>({
    queryKey: ['me'],
    queryFn: async () => {
      const { data } = await apiClient.get<User>('/auth/me');
      return data;
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

export function useLogout() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return () => {
    localStorage.removeItem('access_token');
    Cookies.remove('access_token');
    Cookies.remove('refresh_token');
    queryClient.clear();
    router.push('/auth');
  };
}
