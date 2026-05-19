import { ReactNode } from "react";
import { ClassificationBanner } from "./ClassificationBanner";
import { ClassificationFooter } from "./ClassificationFooter";
import { ClassificationLevel, TLP } from "@/lib/classification";

interface ClassifiedShellProps {
  classification: ClassificationLevel;
  tlp: TLP;
  documentLabel?: string;
  children: ReactNode;
}

/**
 * Envoltorio que monta banner superior + footer inferior con la clasificación
 * indicada. Útil para layouts y páginas individuales que necesitan declarar
 * un nivel mínimo (ej. el group `(admin)` que es siempre CONFIDENCIAL).
 *
 * Añade padding inferior para que el contenido no quede tapado por el footer
 * fijo.
 */
export function ClassifiedShell({
  classification,
  tlp,
  documentLabel,
  children,
}: ClassifiedShellProps) {
  return (
    <>
      <ClassificationBanner
        classification={classification}
        tlp={tlp}
        documentLabel={documentLabel}
      />
      <div className="pb-10">{children}</div>
      <ClassificationFooter classification={classification} tlp={tlp} />
    </>
  );
}
