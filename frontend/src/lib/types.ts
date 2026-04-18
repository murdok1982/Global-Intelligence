export interface User {
  id: string;
  email: string;
  role: 'user' | 'institutional' | 'admin';
  is_active: boolean;
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
  published: boolean;
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
