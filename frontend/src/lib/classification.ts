/**
 * Niveles de clasificación y banderas TLP (Traffic Light Protocol)
 * para datos manejados por la plataforma.
 *
 * Mantiene paridad 1:1 con el backend:
 *   PUBLIC=0, RESTRICTED=1, CONFIDENTIAL=2, SECRET=3
 *
 * Cualquier cambio aquí DEBE sincronizarse con `backend/app/security/classification.py`.
 */

export enum ClassificationLevel {
  PUBLIC = 0,
  RESTRICTED = 1,
  CONFIDENTIAL = 2,
  SECRET = 3,
}

export enum TLP {
  CLEAR = "TLP:CLEAR",
  GREEN = "TLP:GREEN",
  AMBER = "TLP:AMBER",
  AMBER_STRICT = "TLP:AMBER+STRICT",
  RED = "TLP:RED",
}

export const CLASSIFICATION_LABEL: Record<ClassificationLevel, string> = {
  [ClassificationLevel.PUBLIC]: "PÚBLICO",
  [ClassificationLevel.RESTRICTED]: "DIFUSIÓN LIMITADA",
  [ClassificationLevel.CONFIDENTIAL]: "CONFIDENCIAL",
  [ClassificationLevel.SECRET]: "SECRETO",
};

export const CLASSIFICATION_SHORT: Record<ClassificationLevel, string> = {
  [ClassificationLevel.PUBLIC]: "PÚBLICO",
  [ClassificationLevel.RESTRICTED]: "RESTR.",
  [ClassificationLevel.CONFIDENTIAL]: "CONFID.",
  [ClassificationLevel.SECRET]: "SECRETO",
};

export interface ClassificationPalette {
  bg: string;
  text: string;
  border: string;
  ring: string;
}

export const CLASSIFICATION_COLOR: Record<ClassificationLevel, ClassificationPalette> = {
  [ClassificationLevel.PUBLIC]: {
    bg: "bg-emerald-950",
    text: "text-emerald-300",
    border: "border-emerald-500/50",
    ring: "ring-emerald-500/40",
  },
  [ClassificationLevel.RESTRICTED]: {
    bg: "bg-yellow-950",
    text: "text-yellow-300",
    border: "border-yellow-500/50",
    ring: "ring-yellow-500/40",
  },
  [ClassificationLevel.CONFIDENTIAL]: {
    bg: "bg-orange-950",
    text: "text-orange-300",
    border: "border-orange-500/50",
    ring: "ring-orange-500/40",
  },
  [ClassificationLevel.SECRET]: {
    bg: "bg-red-950",
    text: "text-red-300",
    border: "border-red-500/60",
    ring: "ring-red-500/50",
  },
};

export const TLP_DESCRIPTION: Record<TLP, string> = {
  [TLP.CLEAR]: "Difusión sin restricción",
  [TLP.GREEN]: "Comunidad — fuera de canales públicos",
  [TLP.AMBER]: "Need-to-know — organización + clientes",
  [TLP.AMBER_STRICT]: "Need-to-know — sólo organización",
  [TLP.RED]: "Sólo destinatario nominado",
};

/**
 * Verifica si un usuario con un clearance determinado puede acceder a un ítem
 * con cierta clasificación.
 *
 * Regla: el clearance del usuario debe ser >= la clasificación del ítem.
 */
export function canAccess(
  userClearance: ClassificationLevel,
  itemClassification: ClassificationLevel,
): boolean {
  return userClearance >= itemClassification;
}

/**
 * Filtra una lista de ítems clasificados, dejando solo los que el usuario
 * puede ver. Defensa en profundidad — el backend ya debería filtrar con RLS.
 */
export function filterByClearance<T extends { classification?: ClassificationLevel | number | null }>(
  items: readonly T[],
  userClearance: ClassificationLevel,
): T[] {
  return items.filter((item) => {
    // Si el ítem no trae clasificación se asume PÚBLICO (defensa segura: lo visible).
    const cls = (item.classification ?? ClassificationLevel.PUBLIC) as ClassificationLevel;
    return canAccess(userClearance, cls);
  });
}

/**
 * Convierte un valor numérico arbitrario (proveniente del backend o de una
 * cookie) en un `ClassificationLevel` válido. Cualquier valor fuera de rango
 * cae a PUBLIC (el más restrictivo en términos de exposición de datos: no
 * concedemos más permisos de los que el backend confirma).
 */
export function toClassificationLevel(value: unknown): ClassificationLevel {
  const n = typeof value === "number" ? value : Number(value);
  if (Number.isFinite(n) && n >= 0 && n <= 3) {
    return n as ClassificationLevel;
  }
  return ClassificationLevel.PUBLIC;
}

/**
 * Normaliza una cadena TLP arbitraria al enum. Devuelve `TLP.CLEAR` si no
 * coincide con ningún valor conocido — nuevamente, fallback al menos sensible.
 */
export function toTLP(value: unknown): TLP {
  if (typeof value !== "string") return TLP.CLEAR;
  const upper = value.toUpperCase().trim();
  const all = Object.values(TLP) as string[];
  if (all.includes(upper)) return upper as TLP;
  // Acepta también formato sin prefijo "TLP:"
  const withPrefix = `TLP:${upper}`;
  if (all.includes(withPrefix)) return withPrefix as TLP;
  return TLP.CLEAR;
}
