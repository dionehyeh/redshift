import type { FeatureCollection, GeoJsonProperties, Geometry } from "geojson";

export type FieldProfileStatus = "pending" | "building" | "ready" | "failed";
export type FieldWaterSource = "rainfed" | "borewell" | "canal" | "unknown";
export type FieldWaterQuality = "good" | "saline" | "unknown";

export interface FieldListItem {
  id: number;
  name: string;
  lat: number;
  lon: number;
  area_ha: number | null;
  profile_status: FieldProfileStatus;
  climate_cell_id: string | null;
  water_source: FieldWaterSource;
  water_quality: FieldWaterQuality;
  created_at: string;
}

export interface FieldListResponse {
  items: FieldListItem[];
  total: number;
}

export interface FieldCreateResponse {
  field_id: number;
  job_id: string;
  status: "queued";
}

export interface FieldCreateRequest {
  name: string;
  lat: number;
  lon: number;
  area_ha?: number;
  water_source: FieldWaterSource;
  water_quality: FieldWaterQuality;
  boundary_geojson?: string;
}

export interface FieldPatchResponse {
  status: "updated" | "queued";
  field_id: number;
  job_id: string | null;
}

export interface FieldCorrection {
  key: "soil_ph" | "soil_oc" | "soil_texture";
  value: number | string;
  note?: string;
}

export interface FieldPatchRequest {
  name?: string;
  lat?: number;
  lon?: number;
  area_ha?: number;
  water_source?: FieldWaterSource;
  water_quality?: FieldWaterQuality;
  boundary_geojson?: string;
  corrections?: FieldCorrection[];
}

export interface FieldMetric {
  value: string | number | boolean | null;
  source: string;
  resolution: string | null;
  confidence: string;
  estimate?: Record<string, unknown>;
}

export interface FieldProfile {
  id: number;
  farmer_id: number;
  name: string;
  lat: number;
  lon: number;
  area_ha: number | null;
  water_source: FieldWaterSource;
  water_quality: FieldWaterQuality;
  profile_status: FieldProfileStatus;
  profile: Record<string, FieldMetric>;
  gaps: string[];
  climate_cell_id: string | null;
  created_at: string;
}

export interface FeasibleCrop {
  crop_id: number;
  crop_name: string;
  name_ml: string | null;
  family: string | null;
  water_need: string | null;
  class: "suitable" | "marginal" | "not_suitable";
  reason: string;
  start_windows: string[];
  duration_days: number | null;
  computed_at: string | null;
}

export interface FeasibleCropsResponse {
  field_id: number;
  computed_at: string | null;
  suitable: FeasibleCrop[];
  marginal: FeasibleCrop[];
  not_suitable: FeasibleCrop[];
}

export interface FieldHistorySeason {
  id: number;
  crop_id: number | null;
  field_id: number;
  status: string | null;
  start_date: string | null;
  end_date: string | null;
  outcome: string | null;
  loss_percent: number | null;
  suspected_cause: string | null;
  approval_status: string | null;
  approved_cause: string | null;
  approver_role: string | null;
  investment: number | null;
  revenue: number | null;
  created_at: string | null;
  crop_name: string | null;
  name_ml: string | null;
  family: string | null;
  approved_by_name: string | null;
}

export interface FieldHistoryResponse {
  field_id: number;
  total: number;
  seasons: FieldHistorySeason[];
}

export interface TimelineSeries {
  values: (number | null)[];
  source: string;
  resolution: string | null;
  is_normal: boolean;
}

export interface FieldTimeline {
  field_id: number;
  weeks: number[];
  normals: Record<string, (number | null)[]>;
  series: Record<string, TimelineSeries>;
  bands: Record<string, unknown>[];
  source_note: string;
}

export type FieldMapData = FeatureCollection<Geometry, GeoJsonProperties>;
