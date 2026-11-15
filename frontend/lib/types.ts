export type Level = "green" | "amber" | "red";
export type Factor = "water" | "rotation" | "temp" | "soil" | "market" | "timing";
export type Verdict = "Feasible" | "Possible with risk" | "Not suited this season" | "Not assessed";
export type Confidence = "high" | "medium" | "low";

export interface Estimated<T> {
  value: T;
  source: string;
  resolution?: string;
  confidence: Confidence;
  estimate?: { value: T; source: string };
}

export interface CardNarrative {
  why: string;
  risks: string;
  previous_crop_effect: string;
  next_step: string;
  watch_for: string;
  after_this: string;
}

export interface PlanCardData {
  id: number;
  position: number;
  is_existing_rotation: boolean;
  crop: string;
  verdict: Verdict;
  total: number | null;
  factors: Record<Factor, number>;
  colors: Record<Factor, Level>;
  confidence: { level: Confidence; reason: string };
  robustness: { worst_case_total: number | null; holds_up_best: boolean };
  text: CardNarrative;
  notes: string[];
  needs_local_review: string[];
  explainer_keys: string[];
}

export interface Change {
  crop: string;
  factor: Factor;
  from: number;
  to: number;
  message_key: string | null;
}

export interface Scenario {
  rain: number;
  temp: number;
}

export interface RescoreResponse {
  cards: PlanCardData[];
  changes: Change[];
}

export interface Plan {
  plan_id: number;
  outlook: { label: string; factor: number; confidence: Confidence };
  weights: Record<string, number>;
  inputs: { start_week: number; stored_mm: number; stored_basis: string };
  cards: PlanCardData[];
  farmer_choice_card: PlanCardData | null;
  chosen_card_id: number | null;
}

export interface Job {
  job_id: string;
  status: "queued" | "running" | "done" | "done_with_gaps" | "failed";
  step: string;
  progress: number;
  steps: string[];
  error?: string;
}

export interface Finding {
  id: number;
  kind: string;
  weeks: [number, number];
  deviation: string;
  crop_stage: string;
  severity: "low" | "medium" | "high";
  text: string;
  explainer_key: string;
  confidence: Confidence;
  source: string;
  resolution: string;
  review_status: "pending" | "confirmed" | "corrected" | "rejected";
}

export interface FieldItem {
  id: number;
  farmer_id: number;
  name: string;
  lat: number;
  lon: number;
  area_ha?: number;
  water_source: string;
  water_quality: string;
  profile_status: "pending" | "building" | "ready" | "failed";
  created_at: string;
}

export interface UserProfile {
  id: number;
  name: string;
  role: "farmer" | "mentor" | "officer" | "admin";
  language: "en" | "ml";
  contact: string;
  helper_type: "student" | "volunteer" | "college" | "officer" | null;
  market_toggle: "earn_more" | "play_safe" | null;
  default_share_consent: 0 | 1;
}

export interface UserPrefsUpdate {
  language?: "en" | "ml" | null;
  market_toggle?: "earn_more" | "play_safe" | null;
  default_share_consent?: 0 | 1 | null;
}
