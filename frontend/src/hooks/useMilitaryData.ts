'use client';

import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type {
  WeaponListResponse,
  ArmsTransfer,
  MilitaryBase,
  DefenseBudget,
  MilitaryStats,
} from '@/lib/types';

export function useWeapons(
  category?: string,
  origin?: string,
  search?: string,
  page: number = 1,
  size: number = 20
) {
  return useQuery<WeaponListResponse>({
    queryKey: ['military', 'weapons', { category, origin, search, page, size }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (category) params.set('category', category);
      if (origin) params.set('origin', origin);
      if (search) params.set('search', search);
      params.set('page', String(page));
      params.set('size', String(size));
      const { data } = await apiClient.get<WeaponListResponse>(
        `/military/weapons?${params.toString()}`
      );
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useArmsTransfers(
  supplier?: string,
  recipient?: string,
  yearFrom?: number,
  yearTo?: number
) {
  return useQuery<ArmsTransfer[]>({
    queryKey: ['military', 'transfers', { supplier, recipient, yearFrom, yearTo }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (supplier) params.set('supplier', supplier);
      if (recipient) params.set('recipient', recipient);
      if (yearFrom) params.set('year_from', String(yearFrom));
      if (yearTo) params.set('year_to', String(yearTo));
      const { data } = await apiClient.get<ArmsTransfer[]>(
        `/military/transfers?${params.toString()}`
      );
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useMilitaryBases(
  country?: string,
  type?: string,
  foreignOnly?: boolean
) {
  return useQuery<MilitaryBase[]>({
    queryKey: ['military', 'bases', { country, type, foreignOnly }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (country) params.set('country', country);
      if (type) params.set('type', type);
      if (foreignOnly !== undefined) params.set('foreign_only', String(foreignOnly));
      const { data } = await apiClient.get<MilitaryBase[]>(
        `/military/bases?${params.toString()}`
      );
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useDefenseBudgets(country?: string, year?: number) {
  return useQuery<DefenseBudget[]>({
    queryKey: ['military', 'budgets', { country, year }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (country) params.set('country', country);
      if (year) params.set('year', String(year));
      const { data } = await apiClient.get<DefenseBudget[]>(
        `/military/budgets?${params.toString()}`
      );
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useMilitaryStats() {
  return useQuery<MilitaryStats>({
    queryKey: ['military', 'stats'],
    queryFn: async () => {
      const { data } = await apiClient.get<MilitaryStats>('/military/stats');
      return data;
    },
    staleTime: 60 * 1000,
  });
}
