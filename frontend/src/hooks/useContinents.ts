'use client';

import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { Continent, Country } from '@/lib/types';

export function useContinents() {
  return useQuery<Continent[]>({
    queryKey: ['continents'],
    queryFn: async () => {
      const { data } = await apiClient.get<Continent[]>('/continents');
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useContinent(id: string) {
  return useQuery<Continent>({
    queryKey: ['continents', id],
    queryFn: async () => {
      const { data } = await apiClient.get<Continent>(`/continents/${id}`);
      return data;
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

export function useContinentCountries(id: string) {
  return useQuery<Country[]>({
    queryKey: ['continents', id, 'countries'],
    queryFn: async () => {
      const { data } = await apiClient.get<Country[]>(
        `/continents/${id}/countries`
      );
      return data;
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}
