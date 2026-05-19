import { ShieldCheck } from "lucide-react";
import {
  CLASSIFICATION_COLOR,
  CLASSIFICATION_SHORT,
  ClassificationLevel,
} from "@/lib/classification";
import { cn } from "@/lib/utils";

interface ClearanceChipProps {
  clearance: ClassificationLevel;
  className?: string;
}

/**
 * Chip con el nivel de habilitación (clearance) del usuario.
 * Pensado para integrarse junto al avatar en el header.
 */
export function ClearanceChip({ clearance, className }: ClearanceChipProps) {
  const palette = CLASSIFICATION_COLOR[clearance];

  return (
    <span
      className={cn(
        "hidden sm:inline-flex items-center gap-1.5 px-2 py-1 border rounded font-mono text-[10px] uppercase tracking-widest font-bold",
        palette.bg,
        palette.text,
        palette.border,
        className,
      )}
      aria-label={`Clearance del usuario: ${CLASSIFICATION_SHORT[clearance]}`}
    >
      <ShieldCheck size={10} aria-hidden="true" />
      Clearance: {CLASSIFICATION_SHORT[clearance]}
    </span>
  );
}
