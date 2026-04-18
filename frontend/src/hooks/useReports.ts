'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { Report } from '@/lib/types';

export function useReports() {
  return useQuery<Report[]>({
    queryKey: ['reports'],
    queryFn: async () => {
      const { data } = await apiClient.get<Report[]>('/reports');
      return data;
    },
    staleTime: 2 * 60 * 1000,
  });
}

export function useReport(id: string) {
  return useQuery<Report>({
    queryKey: ['reports', id],
    queryFn: async () => {
      const { data } = await apiClient.get<Report>(`/reports/${id}`);
      return data;
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

export function useGenerateReport() {
  const queryClient = useQueryClient();

  return useMutation<Report, Error, { country_iso: string }>({
    mutationFn: async (payload) => {
      const { data } = await apiClient.post<Report>(
        '/reports/generate',
        payload
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}
