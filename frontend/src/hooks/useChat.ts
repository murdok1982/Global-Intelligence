'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { ChatMessage, ChatSession } from '@/lib/types';

export function useCreateSession() {
  const queryClient = useQueryClient();

  return useMutation<ChatSession, Error, { report_id: string }>({
    mutationFn: async (payload) => {
      const { data } = await apiClient.post<ChatSession>(
        '/chat/sessions',
        payload
      );
      return data;
    },
    onSuccess: (session) => {
      queryClient.invalidateQueries({
        queryKey: ['chat', 'sessions', session.id, 'messages'],
      });
    },
  });
}

export function useChatMessages(sessionId: string) {
  return useQuery<ChatMessage[]>({
    queryKey: ['chat', 'sessions', sessionId, 'messages'],
    queryFn: async () => {
      const { data } = await apiClient.get<ChatMessage[]>(
        `/chat/sessions/${sessionId}/messages`
      );
      return data;
    },
    enabled: !!sessionId,
    staleTime: 0,
    refetchOnWindowFocus: false,
  });
}

interface SendMessageResponse {
  message: ChatMessage;
  response: string;
}

export function useSendMessage(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation<SendMessageResponse, Error, { content: string }>({
    mutationFn: async (payload) => {
      const { data } = await apiClient.post<SendMessageResponse>(
        `/chat/sessions/${sessionId}/message`,
        payload
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['chat', 'sessions', sessionId, 'messages'],
      });
    },
  });
}

export function useScenario() {
  return useMutation<
    { result: string },
    Error,
    { report_id: string; variable: string }
  >({
    mutationFn: async (payload) => {
      const { data } = await apiClient.post<{ result: string }>(
        '/chat/scenario',
        payload
      );
      return data;
    },
  });
}
