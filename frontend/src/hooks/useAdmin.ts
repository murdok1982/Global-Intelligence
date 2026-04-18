'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { AdminStats, Contribution, User } from '@/lib/types';

export function useAdminStats() {
  return useQuery<AdminStats>({
    queryKey: ['admin', 'stats'],
    queryFn: async () => {
      const { data } = await apiClient.get<AdminStats>('/admin/stats');
      return data;
    },
    staleTime: 60 * 1000,
  });
}

export function useContributions() {
  return useQuery<Contribution[]>({
    queryKey: ['admin', 'contributions'],
    queryFn: async () => {
      const { data } = await apiClient.get<Contribution[]>(
        '/admin/contributions'
      );
      return data;
    },
    staleTime: 30 * 1000,
  });
}

export function useReviewContribution() {
  const queryClient = useQueryClient();

  return useMutation<
    void,
    Error,
    { id: string; action: 'approve' | 'reject' }
  >({
    mutationFn: async ({ id, action }) => {
      await apiClient.patch(`/admin/contributions/${id}`, { action });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'contributions'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] });
    },
  });
}

export function useAdminUsers(page: number = 1, size: number = 20) {
  return useQuery<User[]>({
    queryKey: ['admin', 'users', { page, size }],
    queryFn: async () => {
      const { data } = await apiClient.get<User[]>(
        `/admin/users?page=${page}&size=${size}`
      );
      return data;
    },
    staleTime: 60 * 1000,
  });
}
