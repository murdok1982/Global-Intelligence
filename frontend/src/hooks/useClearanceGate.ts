'use client';

import { ClassificationLevel, canAccess } from '@/lib/classification';
import { useCurrentUser } from './useCurrentUser';

export interface ClearanceGateState {
  allowed: boolean;
  isLoading: boolean;
}

/**
 * Devuelve si el usuario actual tiene clearance suficiente para acceder a un
 * recurso con el nivel `required`. Mientras se carga el usuario, `allowed`
 * vale `false` para evitar destellos de contenido sensible.
 */
export function useClearanceGate(required: ClassificationLevel): ClearanceGateState {
  const { clearance, isLoading, isAuthenticated } = useCurrentUser();

  if (isLoading) {
    return { allowed: false, isLoading: true };
  }

  if (!isAuthenticated && required > ClassificationLevel.PUBLIC) {
    return { allowed: false, isLoading: false };
  }

  return {
    allowed: canAccess(clearance, required),
    isLoading: false,
  };
}
