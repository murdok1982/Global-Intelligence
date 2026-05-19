'use client';

import { usePathname } from "next/navigation";
import { ClassificationFooter } from "./ClassificationFooter";
import { classifyRoute } from "@/lib/route-classification";
import { ClassificationLevel } from "@/lib/classification";

/**
 * Inserta el footer de clasificación según la ruta actual. Pareja de
 * `ClassificationLayer`.
 */
export function ClassificationFooterLayer() {
  const pathname = usePathname();
  const { classification, tlp } = classifyRoute(pathname);

  if (classification === ClassificationLevel.PUBLIC) {
    return null;
  }

  return <ClassificationFooter classification={classification} tlp={tlp} />;
}
