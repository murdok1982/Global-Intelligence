'use client';

import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { Country, IntelligenceListResponse, Report } from '@/lib/types';

export function useCountry(iso: string) {
  return useQuery<Country>({
    queryKey: ['countries', iso],
    queryFn: async () => {
      const { data } = await apiClient.get<Country>(`/countries/${iso}`);
      return data;
    },
    enabled: !!iso,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCountryIntelligence(
  iso: string,
  category?: string,
  page: number = 1,
  size: number = 20
) {
  return useQuery<IntelligenceListResponse>({
    queryKey: ['countries', iso, 'intelligence', { category, page, size }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (category) params.set('category', category);
      params.set('page', String(page));
      params.set('size', String(size));
      const { data } = await apiClient.get<IntelligenceListResponse>(
        `/countries/${iso}/intelligence?${params.toString()}`
      );
      return data;
    },
    enabled: !!iso,
    staleTime: 2 * 60 * 1000,
  });
}

export function useCountryReports(iso: string) {
  return useQuery<Report[]>({
    queryKey: ['countries', iso, 'reports'],
    queryFn: async () => {
      const { data } = await apiClient.get<Report[]>(
        `/countries/${iso}/reports`
      );
      return data;
    },
    enabled: !!iso,
    staleTime: 5 * 60 * 1000,
  });
}
