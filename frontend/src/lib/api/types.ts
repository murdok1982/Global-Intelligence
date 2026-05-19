/**
 * Tipos compartidos con el backend para la API clasificada.
 *
 * Estos tipos reflejan el contrato del backend tras la refactorización a
 * niveles de clasificación. El campo `clearance_level` del usuario y los
 * campos `classification` / `tlp` de los ítems son obligatorios cuando el
 * recurso es servido por `/api/v1/classified/*`.
 */

import { ClassificationLevel, TLP } from "@/lib/classification";

export type UserRole = "user" | "institutional" | "admin";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  clearance_level: ClassificationLevel;
  mfa_enabled: boolean;
}

export interface IntelligenceItem {
  id: string;
  country_id: string;
  category_id: string;
  agent_source: string;
  content: string;
  classification: ClassificationLevel;
  tlp: TLP;
  admiralty_reliability?: string | null;
  admiralty_credibility?: string | null;
  confidence_score: number;
  created_at: string;
}

export interface IntelligenceListResponse {
  items: IntelligenceItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface DailyReport {
  id: string;
  country_id: string;
  report_date: string;
  executive_summary: string;
  content_json?: string;
  classification: ClassificationLevel;
  tlp: TLP;
  /** Firma digital opcional (P3 — verificación de integridad institucional). */
  signature?: string | null;
  /** Timestamp ISO-8601 del momento en que se firmó el reporte. */
  signed_at?: string | null;
  /** Fingerprint (16 hex) de la pubkey usada para firmar. */
  signature_fingerprint?: string | null;
  /** org_id propietario (si aplica). Necesario para reconstruir el canonical payload. */
  org_id?: string | null;
  /** Timestamp de creación — usado en el canonical payload. */
  created_at?: string | null;
  published: boolean;
}

export interface PremiumReport {
  id: string;
  country_id?: string | null;
  report_date: string;
  executive_summary: string;
  content_json?: string | null;
  content_markdown?: string | null;
  classification: ClassificationLevel;
  tlp: TLP;
  signature?: string | null;
  signed_at?: string | null;
  signature_fingerprint?: string | null;
  org_id?: string | null;
  created_at?: string | null;
  published: boolean;
}

// ---------------------------------------------------------------------------
// Firma criptográfica Ed25519 (P3)
// ---------------------------------------------------------------------------

export interface SigningPubkey {
  /** Clave pública en PEM PKCS#8 SubjectPublicKeyInfo. */
  public_key_pem: string;
  /** Huella corta (16 hex) de sha256(raw_public_key). */
  fingerprint: string;
  algorithm: "Ed25519";
}

export interface ReportSignatureBundle {
  /** Blob base64 producido por ReportSigner.sign — `signature|fingerprint`. */
  signature: string | null;
  /** Hex sha256 del canonical payload recalculado por el backend. */
  canonical_payload_hash: string;
  /** Fingerprint de la pubkey con la que se firmó. */
  public_key_fingerprint: string | null;
}

export interface SignatureVerifyResponse {
  valid: boolean;
  fingerprint: string;
}

export interface RotateSigningKeyResponse {
  new_fingerprint: string;
  archived_old_fingerprint: string | null;
  public_key_pem: string;
}

export interface ClassifiedListMeta {
  /** Clasificación máxima entre los ítems devueltos. */
  max_classification: ClassificationLevel;
  /** TLP más restrictivo presente en la lista. */
  most_restrictive_tlp: TLP;
}

// ---------------------------------------------------------------------------
// MFA (TOTP + recovery codes)
// ---------------------------------------------------------------------------

export interface MfaStatus {
  enrolled: boolean;
  recovery_codes_remaining: number;
}

export interface MfaEnrollResponse {
  provisioning_uri: string;
  secret_b32: string;
  recovery_codes: string[];
}

export interface LoginResponseMfaRequired {
  mfa_required: true;
  challenge_token: string;
  expires_in: number;
}

export interface LoginResponseTokens {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export type LoginResponse = LoginResponseMfaRequired | LoginResponseTokens;

/** Type guard — distingue una respuesta de login que exige MFA. */
export function isMfaRequired(
  response: LoginResponse,
): response is LoginResponseMfaRequired {
  return (response as LoginResponseMfaRequired).mfa_required === true;
}

// ---------------------------------------------------------------------------
// Audit log (cadena hash-encadenada inmutable)
// ---------------------------------------------------------------------------

export type AuditOutcome = "success" | "denied" | "error";

export interface AuditEvent {
  id: string;
  timestamp: string;
  actor_user_id: string | null;
  actor_ip: string | null;
  event_type: string;
  resource_type: string | null;
  resource_id: string | null;
  classification: number | null;
  outcome: AuditOutcome;
  metadata_json: Record<string, unknown> | null;
  prev_hash: string;
  row_hash: string;
}

export interface AuditEventsPage {
  items: AuditEvent[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface AuditVerifyResponse {
  valid: boolean;
  total_events: number;
  broken_at: string | null;
  last_hash: string;
}

export interface AuditEventsFilter {
  event_type?: string;
  actor?: string;
  from?: string;
  to?: string;
  classification?: ClassificationLevel | number;
  outcome?: AuditOutcome;
  page?: number;
  size?: number;
}
