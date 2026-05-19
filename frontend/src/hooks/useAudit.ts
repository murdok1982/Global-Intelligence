'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type {
  AuditEventsFilter,
  AuditEventsPage,
  AuditVerifyResponse,
} from '@/lib/api/types';

const DEFAULT_PAGE_SIZE = 25;

function buildParams(filter: AuditEventsFilter): Record<string, string | number> {
  const params: Record<string, string | number> = {
    page: filter.page ?? 1,
    size: filter.size ?? DEFAULT_PAGE_SIZE,
  };
  if (filter.event_type) params.event_type = filter.event_type;
  if (filter.actor) params.actor = filter.actor;
  if (filter.from) params.from = filter.from;
  if (filter.to) params.to = filter.to;
  if (typeof filter.classification === 'number') {
    params.classification = filter.classification;
  }
  if (filter.outcome) params.outcome = filter.outcome;
  return params;
}

export function useAuditEvents(filter: AuditEventsFilter) {
  return useQuery<AuditEventsPage>({
    queryKey: ['audit', 'events', filter],
    queryFn: async () => {
      const { data } = await apiClient.get<AuditEventsPage>(
        '/classified/admin/audit/events',
        { params: buildParams(filter) },
      );
      return data;
    },
    placeholderData: (prev) => prev,
    staleTime: 30 * 1000,
    retry: false,
  });
}

export function useAuditVerify() {
  return useMutation<AuditVerifyResponse, Error, void>({
    mutationFn: async () => {
      const { data } = await apiClient.get<AuditVerifyResponse>(
        '/classified/admin/audit/verify',
      );
      return data;
    },
  });
}
