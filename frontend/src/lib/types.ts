import { ClassificationLevel, TLP } from "@/lib/classification";

export interface User {
  id: string;
  email: string;
  role: 'user' | 'institutional' | 'admin';
  is_active: boolean;
  /** Nivel de habilitación del usuario. Por defecto PUBLIC (0). */
  clearance_level?: ClassificationLevel;
  /** Indica si el usuario tiene MFA activado. */
  mfa_enabled?: boolean;
}

export interface Continent {
  id: string;
  name: string;
  code: string;
  country_count: number;
}

export interface CountryProfile {
  overall_risk_score: 'Low' | 'Medium' | 'High' | 'Critical';
}

export interface Country {
  id: string;
  name: string;
  iso_code: string;
  continent_id: string;
  profile?: CountryProfile;
}

export interface IntelligenceItem {
  id: string;
  country_id: string;
  category_id: string;
  agent_source: string;
  content: string;
  confidence_score: number;
  created_at: string;
  /** Nivel de clasificación. Opcional para compatibilidad con endpoints públicos. */
  classification?: ClassificationLevel;
  /** Marca TLP del ítem. */
  tlp?: TLP;
  admiralty_reliability?: string | null;
  admiralty_credibility?: string | null;
}

export interface IntelligenceListResponse {
  items: IntelligenceItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface Report {
  id: string;
  country_id: string;
  report_date: string;
  executive_summary: string;
  content_json?: string;
  content_markdown?: string | null;
  published: boolean;
  /** Clasificación del reporte. Opcional por compatibilidad. */
  classification?: ClassificationLevel;
  /** Marca TLP. */
  tlp?: TLP;
  /** Firma digital opcional (P3). */
  signature?: string | null;
  /** Timestamp ISO-8601 de cuando se firmó. */
  signed_at?: string | null;
  /** Fingerprint (16 hex) de la pubkey usada para firmar. */
  signature_fingerprint?: string | null;
  /** Organización propietaria — entra al canonical payload si está presente. */
  org_id?: string | null;
  /** Timestamp de creación del reporte. */
  created_at?: string | null;
}

export interface ChatSession {
  id: string;
  user_id: string;
  report_bind_id: string;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface AdminStats {
  users: number;
  countries: number;
  intelligence_items: number;
  reports: number;
  pending_contributions: number;
}

export interface Contribution {
  id: string;
  alias?: string;
  country: string;
  category: string;
  description: string;
  status: string;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface RegisterResponse {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
}

export interface RefreshResponse {
  access_token: string;
  token_type: string;
}

export interface IntakeRequest {
  message: string;
  session_id?: string;
}

export interface IntakeResponse {
  response: string;
  session_id: string;
}

export interface Weapon {
  id: string;
  name: string;
  designation: string;
  origin_country: string;
  category: string;
  cost_usd: number | null;
  key_specs: Record<string, string>;
  description?: string;
  image_url?: string | null;
}

export interface WeaponListResponse {
  items: Weapon[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ArmsTransfer {
  id: string;
  supplier_country: string;
  recipient_country: string;
  weapon_system: string;
  year: number;
  value_usd: number | null;
  status: string;
  lat_supplier?: number;
  lng_supplier?: number;
  lat_recipient?: number;
  lng_recipient?: number;
}

export interface MilitaryBase {
  id: string;
  name: string;
  country: string;
  type: string;
  lat: number;
  lng: number;
  is_foreign: boolean;
  personnel_count?: number | null;
  status?: string;
}

export interface DefenseBudget {
  id: string;
  country: string;
  year: number;
  budget_usd: number;
  gdp_percentage: number | null;
  source?: string | null;
}

export interface MilitaryStats {
  total_weapons: number;
  total_transfers: number;
  total_bases: number;
  global_spend_usd: number;
}
