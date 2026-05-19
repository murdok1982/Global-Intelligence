/**
 * Cliente WebCrypto para verificación de firmas Ed25519 de reportes.
 *
 * El backend firma un canonical JSON payload sobre el reporte (ver
 * `backend/app/services/signing.py::ReportSigner.canonical_payload`).
 * Aquí reconstruimos esos bytes de forma idéntica y verificamos la
 * firma en el navegador con WebCrypto API.
 *
 * Algoritmo: Ed25519 (RFC 8032) en clave PKCS#8 SubjectPublicKeyInfo.
 *
 * Compatibilidad de navegador:
 * - Chromium 113+
 * - Safari 17+
 * - Firefox 130+ (con `dom.crypto.subtle.ed25519.enabled` en algunas builds)
 *
 * Si `crypto.subtle.importKey("Ed25519", ...)` lanza, el caller debe usar
 * el fallback server-side `POST /public/signing/verify`.
 *
 * El blob de firma del backend tiene la forma:
 *   base64(raw_signature_64_bytes || "|" || utf8_fingerprint_16_chars)
 * Hay que extraer los 64 bytes de firma cruda antes de pasarlos a WebCrypto.
 */

import type { Report } from "@/lib/types";
import type { DailyReport, PremiumReport } from "@/lib/api/types";

/** Tipos de reporte que pueden estar firmados. */
export type SignedReport = Report | DailyReport | PremiumReport;

// ---------------------------------------------------------------------------
// Detección de soporte
// ---------------------------------------------------------------------------

let _ed25519SupportCache: boolean | null = null;

/**
 * Devuelve true si WebCrypto soporta importKey/verify con Ed25519.
 * Cachea el resultado tras el primer chequeo — la respuesta no cambia
 * en runtime.
 */
export async function isEd25519Supported(): Promise<boolean> {
  if (_ed25519SupportCache !== null) return _ed25519SupportCache;
  if (typeof crypto === "undefined" || !crypto.subtle) {
    _ed25519SupportCache = false;
    return false;
  }
  try {
    // Intento ligero: generamos una clave pública mínima inválida.
    // Si lanza por "Ed25519 unsupported" capturamos. Si lanza por
    // formato (que es lo esperado en algunos navegadores que SÍ soportan
    // pero rechazan los bytes), entonces sí está soportado.
    // Estrategia más fiable: usar generateKey.
    await crypto.subtle.generateKey("Ed25519", false, ["sign", "verify"]);
    _ed25519SupportCache = true;
  } catch {
    _ed25519SupportCache = false;
  }
  return _ed25519SupportCache;
}

// ---------------------------------------------------------------------------
// Codecs base64 / PEM
// ---------------------------------------------------------------------------

/** Decodifica una cadena base64 estándar (con o sin padding) a Uint8Array. */
export function base64ToBytes(b64: string): Uint8Array {
  const clean = b64.replace(/\s+/g, "");
  const bin = atob(clean);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

/** Codifica Uint8Array a base64. */
export function bytesToBase64(bytes: Uint8Array): string {
  let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}

/** Convierte un Uint8Array a hex string lowercase. */
export function bytesToHex(bytes: Uint8Array): string {
  let out = "";
  for (let i = 0; i < bytes.length; i++) {
    const h = bytes[i].toString(16);
    out += h.length === 1 ? "0" + h : h;
  }
  return out;
}

/** Parse PEM SubjectPublicKeyInfo → ArrayBuffer DER. */
export function pemToArrayBuffer(pem: string): ArrayBuffer {
  const b64 = pem
    .replace(/-----BEGIN [^-]+-----/g, "")
    .replace(/-----END [^-]+-----/g, "")
    .replace(/\s+/g, "");
  const bytes = base64ToBytes(b64);
  return toArrayBuffer(bytes);
}

/**
 * Copia los bytes a un ArrayBuffer fresco. Necesario porque
 * `Uint8Array.buffer` puede ser tipado como `ArrayBuffer | SharedArrayBuffer`
 * en TS estricto y WebCrypto exige `ArrayBuffer` puro.
 */
function toArrayBuffer(bytes: Uint8Array): ArrayBuffer {
  const out = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(out).set(bytes);
  return out;
}

// ---------------------------------------------------------------------------
// SHA-256 helper
// ---------------------------------------------------------------------------

/** Calcula sha256 de un payload y devuelve hex lowercase. */
export async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const hash = await crypto.subtle.digest("SHA-256", toArrayBuffer(bytes));
  return bytesToHex(new Uint8Array(hash));
}

// ---------------------------------------------------------------------------
// Canonical payload — DEBE coincidir byte-a-byte con backend
// ---------------------------------------------------------------------------

/**
 * Re-implementación del `ReportSigner.canonical_payload` del backend.
 *
 * Reglas:
 * 1. Solo se incluyen campos cuyo valor no sea `null` ni `undefined`
 *    (mismo criterio que `getattr(report, x, None) is not None` en
 *    Python).
 * 2. `JSON.stringify` con `sort_keys=True` equivalente — usamos un
 *    helper que ordena las keys alfabéticamente.
 * 3. Separadores tight `","` y `":"` (sin espacios). El default de
 *    `JSON.stringify` ya no añade espacios, así que basta con no pasar
 *    el tercer argumento.
 * 4. UTF-8 al final.
 *
 * Campos en el payload (todos opcionales, se incluyen solo si están):
 *   id, classification (int), tlp (str), org_id, executive_summary,
 *   content_json, content_markdown, report_date (ISO), created_at (ISO)
 *
 * Si un día el backend cambia el orden o añade campos, este helper
 * debe sincronizarse — es un wire-breaking change.
 */
export function buildCanonicalPayload(report: SignedReport): Uint8Array {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const body: Record<string, any> = {};

  if (report.id != null) body["id"] = String(report.id);
  if (report.classification != null) {
    body["classification"] = Number(report.classification);
  }
  if (report.tlp != null) body["tlp"] = String(report.tlp);

  const orgId = (report as { org_id?: string | null }).org_id;
  if (orgId != null) body["org_id"] = String(orgId);

  if (report.executive_summary != null) {
    body["executive_summary"] = report.executive_summary;
  }
  if (report.content_json != null) {
    body["content_json"] = report.content_json;
  }
  const contentMd = (report as { content_markdown?: string | null }).content_markdown;
  if (contentMd != null) {
    body["content_markdown"] = contentMd;
  }

  if (report.report_date != null) {
    body["report_date"] = isoLike(report.report_date);
  }
  const createdAt = (report as { created_at?: string | null }).created_at;
  if (createdAt != null) {
    body["created_at"] = isoLike(createdAt);
  }

  const serialized = stableStringify(body);
  return new TextEncoder().encode(serialized);
}

/**
 * El backend usa `value.isoformat()` para datetimes. Si el frontend ya
 * recibe el campo como string ISO, lo dejamos tal cual (paridad). Si
 * recibe un Date lo serializamos sin zona si es naive — pero los
 * endpoints actuales devuelven siempre string ISO así que rara vez
 * entraremos en este branch.
 */
function isoLike(value: unknown): string {
  if (value instanceof Date) {
    // Mantener offset si lo trae (mismo isoformat() de Python).
    return value.toISOString();
  }
  return String(value);
}

/**
 * JSON.stringify con keys ordenadas alfabéticamente — equivalente a
 * `json.dumps(..., sort_keys=True, separators=(",", ":"))` en Python.
 *
 * No soporta ciclos. Soporta primitivos, arrays y objetos planos —
 * suficiente para nuestro payload, que solo contiene strings, números
 * e (eventualmente) un content_json ya serializado como string.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function stableStringify(value: any): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return "[" + value.map((v) => stableStringify(v)).join(",") + "]";
  }
  const keys = Object.keys(value).sort();
  const parts: string[] = [];
  for (const k of keys) {
    const v = value[k];
    if (v === undefined) continue;
    parts.push(JSON.stringify(k) + ":" + stableStringify(v));
  }
  return "{" + parts.join(",") + "}";
}

// ---------------------------------------------------------------------------
// Verificación Ed25519
// ---------------------------------------------------------------------------

/**
 * Parsea el blob de firma del backend a la firma cruda Ed25519 (64 bytes).
 *
 * Formato del backend: base64(raw_64_bytes || "|" || ascii_fingerprint).
 * Devuelve null si el blob es inválido (longitud, separador o base64).
 */
export function extractRawSignature(signatureBlob: string): {
  signature: Uint8Array;
  fingerprint: string;
} | null {
  try {
    const all = base64ToBytes(signatureBlob);
    // 64 firma + 1 separador + 16 fingerprint = 81 bytes mínimo.
    if (all.length < 64 + 1 + 1) return null;
    const sig = all.slice(0, 64);
    if (all[64] !== 0x7c /* '|' */) return null;
    const fpBytes = all.slice(65);
    const fp = new TextDecoder("ascii").decode(fpBytes);
    return { signature: sig, fingerprint: fp };
  } catch {
    return null;
  }
}

/**
 * Verifica una firma Ed25519 sobre un canonical payload usando WebCrypto.
 *
 * @param publicKeyPem - clave pública en PEM PKCS#8 SubjectPublicKeyInfo
 * @param canonicalPayload - bytes que el backend firmó
 * @param signatureBlob - blob completo `base64(sig||"|"||fingerprint)`
 *                        tal como lo entrega `GET /reports/{id}/signature`
 * @throws Error("ED25519_UNSUPPORTED") si el navegador no soporta Ed25519.
 * @throws Error("INVALID_SIGNATURE_BLOB") si el blob tiene formato erróneo.
 * @returns true si la firma es válida, false si la pubkey no firma esos bytes.
 */
export async function verifyEd25519(
  publicKeyPem: string,
  canonicalPayload: Uint8Array,
  signatureBlob: string,
): Promise<boolean> {
  if (!(await isEd25519Supported())) {
    throw new Error("ED25519_UNSUPPORTED");
  }

  const parsed = extractRawSignature(signatureBlob);
  if (!parsed) {
    throw new Error("INVALID_SIGNATURE_BLOB");
  }

  const keyDer = pemToArrayBuffer(publicKeyPem);

  // WebCrypto importKey con algoritmo Ed25519, formato spki (= SubjectPublicKeyInfo).
  let key: CryptoKey;
  try {
    key = await crypto.subtle.importKey(
      "spki",
      keyDer,
      { name: "Ed25519" } as AlgorithmIdentifier,
      false,
      ["verify"],
    );
  } catch {
    throw new Error("ED25519_UNSUPPORTED");
  }

  const sigBuffer = toArrayBuffer(parsed.signature);
  const payloadBuffer = toArrayBuffer(canonicalPayload);

  return await crypto.subtle.verify(
    { name: "Ed25519" } as AlgorithmIdentifier,
    key,
    sigBuffer,
    payloadBuffer,
  );
}
