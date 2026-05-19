'use client';

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { ClassificationBanner } from "./ClassificationBanner";
import { classifyRoute } from "@/lib/route-classification";
import { ClassificationLevel } from "@/lib/classification";

const BANNER_HEIGHT_PX = 36;

/**
 * Monta el banner superior de clasificación y publica un atributo
 * `data-classified` en `<body>` que la app usa para desplazar el header
 * y la sidebar por debajo del banner.
 *
 * No renderiza nada en rutas públicas.
 */
export function ClassificationLayer() {
  const pathname = usePathname();
  const { classification, tlp } = classifyRoute(pathname);
  const active = classification !== ClassificationLevel.PUBLIC;

  useEffect(() => {
    const body = typeof document !== "undefined" ? document.body : null;
    if (!body) return;
    if (active) {
      body.dataset.classified = "true";
      body.style.setProperty("--classification-banner-h", `${BANNER_HEIGHT_PX}px`);
    } else {
      delete body.dataset.classified;
      body.style.setProperty("--classification-banner-h", "0px");
    }
    return () => {
      body.style.setProperty("--classification-banner-h", "0px");
      delete body.dataset.classified;
    };
  }, [active]);

  if (!active) return null;

  return <ClassificationBanner classification={classification} tlp={tlp} />;
}
