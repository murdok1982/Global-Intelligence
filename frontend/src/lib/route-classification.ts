import { ClassificationLevel, TLP } from "./classification";

/**
 * Mapeo declarativo entre rutas de la app y su clasificación mínima.
 *
 * Heurística:
 *  — `/admin/*`     → CONFIDENCIAL (TLP:AMBER+STRICT)
 *  — `/reports/*`   → RESTRINGIDO  (TLP:AMBER)
 *  — `/contribute`  → RESTRINGIDO  (TLP:AMBER)  — toma de aportes sensibles
 *  — `/dashboard`   → RESTRINGIDO  (TLP:AMBER)
 *  — Resto          → PÚBLICO     (TLP:CLEAR)
 *
 * Se evalúan por prefijo, de más específico a menos específico.
 */
export interface RouteClassification {
  classification: ClassificationLevel;
  tlp: TLP;
}

interface RouteRule extends RouteClassification {
  prefix: string;
}

const RULES: ReadonlyArray<RouteRule> = [
  { prefix: "/admin", classification: ClassificationLevel.CONFIDENTIAL, tlp: TLP.AMBER_STRICT },
  { prefix: "/reports", classification: ClassificationLevel.RESTRICTED, tlp: TLP.AMBER },
  { prefix: "/contribute", classification: ClassificationLevel.RESTRICTED, tlp: TLP.AMBER },
  { prefix: "/dashboard", classification: ClassificationLevel.RESTRICTED, tlp: TLP.AMBER },
];

const PUBLIC_DEFAULT: RouteClassification = {
  classification: ClassificationLevel.PUBLIC,
  tlp: TLP.CLEAR,
};

export function classifyRoute(pathname: string | null | undefined): RouteClassification {
  if (!pathname) return PUBLIC_DEFAULT;
  for (const rule of RULES) {
    if (pathname === rule.prefix || pathname.startsWith(`${rule.prefix}/`)) {
      return { classification: rule.classification, tlp: rule.tlp };
    }
  }
  return PUBLIC_DEFAULT;
}

export function isClassifiedRoute(pathname: string | null | undefined): boolean {
  return classifyRoute(pathname).classification > ClassificationLevel.PUBLIC;
}
