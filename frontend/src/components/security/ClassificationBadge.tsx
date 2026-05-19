import { Lock } from "lucide-react";
import {
  CLASSIFICATION_COLOR,
  CLASSIFICATION_LABEL,
  CLASSIFICATION_SHORT,
  ClassificationLevel,
  TLP,
} from "@/lib/classification";
import { cn } from "@/lib/utils";

interface ClassificationBadgeProps {
  classification: ClassificationLevel;
  tlp?: TLP;
  /** Si es true muestra la etiqueta abreviada. Útil para listados densos. */
  short?: boolean;
  /** Oculta el icono. */
  hideIcon?: boolean;
  className?: string;
}

/**
 * Chip pequeño con la clasificación (y opcionalmente TLP) — apto para tarjetas,
 * listados y filas de tabla. Refleja el mismo color-coding que el banner.
 */
export function ClassificationBadge({
  classification,
  tlp,
  short = false,
  hideIcon = false,
  className,
}: ClassificationBadgeProps) {
  const palette = CLASSIFICATION_COLOR[classification];
  const label = short
    ? CLASSIFICATION_SHORT[classification]
    : CLASSIFICATION_LABEL[classification];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 border rounded font-mono text-[10px] uppercase tracking-widest font-bold",
        palette.bg,
        palette.text,
        palette.border,
        className,
      )}
      aria-label={`Clasificación ${CLASSIFICATION_LABEL[classification]}${tlp ? `, ${tlp}` : ""}`}
    >
      {!hideIcon && <Lock size={10} aria-hidden="true" />}
      <span>{label}</span>
      {tlp && (
        <>
          <span aria-hidden="true" className="opacity-50">·</span>
          <span>{tlp}</span>
        </>
      )}
    </span>
  );
}
