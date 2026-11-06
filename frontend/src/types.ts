export type Language = 'en' | 'hi';
export type Need = 'internet' | 'backup' | 'mobile' | 'whatsapp' | 'email' | 'security' | 'cctv' | 'billing' | 'website' | 'multisite';
export type Eligibility = 'eligible' | 'conditional' | 'ineligible';
export type BusinessType = 'shop' | 'office' | 'clinic' | 'restaurant' | 'manufacturing' | 'other';
export type Connection = 'none' | 'hotspot' | 'broadband' | 'leased_line';
export type GSTINClaim = 'yes' | 'no' | 'unsure';
export interface Profile {
  business_type: BusinessType;
  city_tier: 1 | 2;
  employees: number;
  sites: number;
  monthly_budget: number;
  current_internet: Connection;
  gstin_claim: GSTINClaim;
  needs: Need[];
  language: Language;
}
export interface BusinessForm {
  business_type: BusinessType | '';
  city_tier: '1' | '2' | '';
  employees: string;
  sites: string;
  monthly_budget: string;
  current_internet: Connection | '';
  gstin_claim: GSTINClaim;
  needs: Need[];
}
export interface Reason { code: string; message: string; message_hi: string }
export interface Explanation { message: string; message_hi: string }
export interface Product {
  product_id: string;
  category: string;
  name: string;
  description: string;
  unit: string;
  monthly_price: number;
  monthly_max: number;
  setup_fee: number;
  contract_months: number;
  requires_one_of: string[];
  status: Eligibility;
  reasons: Reason[];
}
export interface BundleItem { product_id: string; quantity: number }
export interface QuoteLine extends Product { quantity: number; monthly_total: number; setup_total: number }
export interface Quote {
  items: QuoteLine[];
  status: Eligibility;
  monthly_total: number;
  setup_total: number;
  first_month_estimate: number;
  over_budget_by: number;
  budget_provided: boolean;
  catalogue_checks_pass: boolean;
  ready_to_order: false;
}
export interface Recommendations {
  quote: Quote | null;
  catalogue: Product[];
  explanations: Record<string, Explanation>;
  unmet_needs: {need: Need; reasons: Reason[]}[];
  sizing_note: string;
  sizing_note_hi: string;
}
export interface Draft {
  business_type: BusinessType | null;
  employees: number | null;
  sites: number | null;
  monthly_budget: number | null;
  current_internet: Connection | null;
  gstin_claim: GSTINClaim | null;
  needs: Need[];
  follow_up: string;
}
export interface AdvisorReply {
  mode: 'gemini' | 'guided';
  draft: Draft | null;
  reason?: string;
  message: string;
  message_hi?: string;
  retryable?: boolean;
}
export interface LookupReply {
  verification_token: string;
  status: string;
  masked_gstin: string;
}
