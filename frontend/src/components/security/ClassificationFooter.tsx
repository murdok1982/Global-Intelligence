import {
  CLASSIFICATION_COLOR,
  CLASSIFICATION_LABEL,
  ClassificationLevel,
  TLP,
} from "@/lib/classification";
import { cn } from "@/lib/utils";

interface ClassificationFooterProps {
  classification: ClassificationLevel;
  tlp: TLP;
}

/**
 * Pie de página obligatorio en vistas clasificadas. Reglas marca-agua
 * institucionales: clasificación, TLP y recordatorio de need-to-know.
 *
 * Fija en la base del viewport. No interactiva.
 */
export function ClassificationFooter({
  classification,
  tlp,
}: ClassificationFooterProps) {
  const palette = CLASSIFICATION_COLOR[classification];

  return (
    <footer
      role="contentinfo"
      aria-label="Pie de clasificación del documento"
      className={cn(
        "fixed bottom-0 left-0 right-0 z-[55] w-full border-t-2 px-4 py-1.5 font-mono uppercase tracking-widest text-center select-none",
        palette.bg,
        palette.text,
        palette.border,
      )}
    >
      <p className="text-[10px] font-bold">
        Documento {CLASSIFICATION_LABEL[classification]}
        <span aria-hidden="true" className="opacity-50 mx-2">·</span>
        Difusión sujeta a need-to-know
        <span aria-hidden="true" className="opacity-50 mx-2">·</span>
        {tlp}
      </p>
    </footer>
  );
}
