import { Lock, ShieldAlert } from "lucide-react";
import {
  CLASSIFICATION_COLOR,
  CLASSIFICATION_LABEL,
  ClassificationLevel,
  TLP,
} from "@/lib/classification";
import { cn } from "@/lib/utils";

interface ClassificationBannerProps {
  classification: ClassificationLevel;
  tlp: TLP;
  /** Variante compacta: sin texto descriptivo, sólo etiquetas. */
  compact?: boolean;
  /** Texto opcional adicional (ej. nombre del documento). */
  documentLabel?: string;
}

/**
 * Banner fijo de cabecera para vistas clasificadas.
 *
 * — Sticky, z-index alto, no se puede cerrar.
 * — Color según nivel de clasificación.
 * — Muestra clasificación + TLP + recordatorio de auditoría.
 * — `role="alert"` para clasificaciones >= CONFIDENCIAL.
 */
export function ClassificationBanner({
  classification,
  tlp,
  compact = false,
  documentLabel,
}: ClassificationBannerProps) {
  const palette = CLASSIFICATION_COLOR[classification];
  const isHighRisk = classification >= ClassificationLevel.CONFIDENTIAL;
  const Icon = isHighRisk ? ShieldAlert : Lock;

  return (
    <div
      role={isHighRisk ? "alert" : "status"}
      aria-live={isHighRisk ? "assertive" : "polite"}
      aria-label={`Información ${CLASSIFICATION_LABEL[classification]} ${tlp}`}
      className={cn(
        "fixed top-0 left-0 right-0 z-[60] w-full border-b-2 px-4 py-2 font-mono uppercase tracking-widest select-none",
        palette.bg,
        palette.text,
        palette.border,
      )}
    >
      <div className="flex items-center justify-between gap-4 max-w-screen-2xl mx-auto">
        <div className="flex items-center gap-3 flex-shrink-0">
          <Icon size={16} aria-hidden="true" className="flex-shrink-0" />
          <span className="text-xs font-bold tabular-nums">
            {CLASSIFICATION_LABEL[classification]}
          </span>
          <span aria-hidden="true" className="opacity-60">·</span>
          <span className="text-xs font-bold">{tlp}</span>
          {documentLabel && (
            <>
              <span aria-hidden="true" className="opacity-60">·</span>
              <span className="text-[10px] opacity-80 normal-case">
                {documentLabel}
              </span>
            </>
          )}
        </div>

        {!compact && (
          <p className="text-[10px] opacity-80 hidden md:block text-right normal-case tracking-normal">
            Esta vista contiene información clasificada. Quedan registradas todas las acciones.
          </p>
        )}
      </div>
    </div>
  );
}
