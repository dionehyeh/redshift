export type SeasonOutcome = "good" | "average" | "poor" | "failed";
export type AnalysisStatus =
  | "not_started"
  | "queued"
  | "running"
  | "done"
  | "done_with_gaps"
  | "failed";

export interface CropOption {
  id: string;
  name: { en: string; ml: string };
  family: string;
  duration_days: number;
  water_need: string;
  market: string;
}

export interface CropListResponse {
  items: CropOption[];
}

export interface SeasonRecord {
  id: number;
  field_id: number;
  crop_id: number | null;
  crop: string | null;
  status: string;
  start_date: string | null;
  end_date: string | null;
  outcome: SeasonOutcome | null;
  loss_percent: number | null;
  suspected_cause: string | null;
  investment: number | null;
  revenue: number | null;
  approval_status: string;
  approved_cause: string | null;
  approver_role: string | null;
}

export interface SeasonCreateResponse {
  id: number;
  field_id: number;
  status: "completed";
  crop: string;
  approval_status: string;
}

export interface SeasonPatchRequest {
  crop?: string;
  start_date?: string;
  end_date?: string;
  outcome?: SeasonOutcome;
  loss_percent?: number | null;
  suspected_cause?: string | null;
  investment?: number | null;
  revenue?: number | null;
}

export interface SeasonAnalysisStartResponse {
  season_id: number;
  job_id: string;
  status: "queued";
}

export interface SeasonFinding {
  id: number;
  kind: string;
  weeks: [number, number];
  deviation: string;
  unit: string | null;
  crop_stage: string;
  severity: string;
  confidence: string;
  source: string;
  resolution: string;
  text: string;
  explainer_key: string | null;
  review_status: "pending" | "confirmed" | "corrected" | "rejected";
}

export interface LikelyCause {
  cause: string;
  from_finding?: string;
  weeks?: [number, number];
  stage?: string;
}

export interface LikelyCauses {
  suspected: LikelyCause[];
  farmer_cause: string | null;
  not_assessable: string[];
}

export interface SeasonAnalysis {
  season_id: number;
  approval_status: string;
  analysis_status: AnalysisStatus;
  job_id: string | null;
  comparison_years: string | null;
  findings: SeasonFinding[];
  gaps: string[];
  likely_causes: LikelyCauses | null;
  followup_question: string | null;
  analysis_error: string | null;
}

export interface FindingReviewResponse {
  finding_id: number;
  review_status: SeasonFinding["review_status"];
  verified_level: number;
  approved_cause: string | null;
}
