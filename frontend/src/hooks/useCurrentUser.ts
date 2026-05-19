'use client';

import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { User } from '@/lib/types';
import {
  ClassificationLevel,
  toClassificationLevel,
} from '@/lib/classification';

export interface CurrentUserState {
  user: User | null;
  clearance: ClassificationLevel;
  isAuthenticated: boolean;
  isLoading: boolean;
  isError: boolean;
}

/**
 * Hook canónico para obtener al usuario autenticado junto con su nivel de
 * clearance normalizado.
 *
 * Endpoint: `GET /auth/me` (gestionado por el cliente axios con interceptor
 * JWT). El backend devuelve `clearance_level` como número 0-3; aquí lo
 * normalizamos a `ClassificationLevel` defensivamente (cualquier valor fuera
 * de rango cae a PUBLIC).
 *
 * Persistencia del JWT: ya lo gestiona `apiClient` mediante token en memoria +
 * refresh cookie. Este hook no toca cookies.
 */
export function useCurrentUser(): CurrentUserState {
  const { data, isLoading, isError } = useQuery<User>({
    queryKey: ['me'],
    queryFn: async () => {
      const { data } = await apiClient.get<User>('/auth/me');
      return data;
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const user = data ?? null;
  const clearance = user
    ? toClassificationLevel(user.clearance_level)
    : ClassificationLevel.PUBLIC;

  return {
    user,
    clearance,
    isAuthenticated: !!user,
    isLoading,
    isError,
  };
}
