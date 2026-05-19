'use client';

import { ReactNode } from "react";
import { Lock } from "lucide-react";
import {
  CLASSIFICATION_LABEL,
  ClassificationLevel,
} from "@/lib/classification";
import { useClearanceGate } from "@/hooks/useClearanceGate";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface ClearanceGateProps {
  required: ClassificationLevel;
  children: ReactNode;
  /** Mensaje personalizado para el placeholder. */
  fallbackMessage?: string;
  className?: string;
}

/**
 * Wrapper que oculta su contenido al usuario si no tiene clearance suficiente.
 *
 * Estados:
 *  — `isLoading`: skeleton.
 *  — `allowed`: renderiza `children`.
 *  — `!allowed`: placeholder "INFORMACIÓN RETENIDA".
 *
 * Útil para secciones individuales dentro de páginas mixtas (ej. un widget de
 * panel que mezcla datos PÚBLICOS y CONFIDENCIALES).
 */
export function ClearanceGate({
  required,
  children,
  fallbackMessage,
  className,
}: ClearanceGateProps) {
  const { allowed, isLoading } = useClearanceGate(required);

  if (isLoading) {
    return <Skeleton className={cn("h-24 w-full rounded", className)} />;
  }

  if (!allowed) {
    return (
      <div
        role="status"
        aria-label={`Información retenida — requiere clearance ${CLASSIFICATION_LABEL[required]}`}
        className={cn(
          "flex flex-col items-center justify-center gap-2 p-6 border border-dashed border-neutral-700 bg-neutral-900/40 rounded text-neutral-500 font-mono text-xs uppercase tracking-widest",
          className,
        )}
      >
        <Lock size={20} aria-hidden="true" className="opacity-60" />
        <p className="font-bold">Información retenida</p>
        <p className="text-[10px] opacity-80 normal-case tracking-normal text-center max-w-sm">
          {fallbackMessage ??
            `Requiere clearance ${CLASSIFICATION_LABEL[required]} o superior.`}
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
