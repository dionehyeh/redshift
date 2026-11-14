-- Migration 001: Initial Schema
-- Matches backend/data/schema.sql

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  role TEXT NOT NULL CHECK (role IN ('farmer', 'mentor', 'officer', 'admin')),
  helper_type TEXT CHECK (helper_type IN ('student', 'volunteer', 'college', 'officer', NULL)),
  name TEXT NOT NULL,
  language TEXT DEFAULT 'en' CHECK (language IN ('en', 'ml')),
  contact TEXT UNIQUE NOT NULL,
  clerk_user_id TEXT UNIQUE,
  password_hash TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS farmer_prefs (
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  market_toggle TEXT CHECK (market_toggle IN ('earn_more', 'play_safe', NULL)),
  default_share_consent INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fields (
  id SERIAL PRIMARY KEY,
  farmer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  boundary_geojson TEXT,
  area_ha REAL,
  elevation_m REAL,
  slope TEXT,
  flood_prone INTEGER DEFAULT 0,
  drainage TEXT,
  soil_ph REAL,
  soil_oc REAL,
  soil_texture TEXT,
  soil_source TEXT,
  soil_confidence TEXT,
  water_source TEXT DEFAULT 'unknown' CHECK (water_source IN ('rainfed', 'borewell', 'canal', 'unknown')),
  water_quality TEXT DEFAULT 'unknown' CHECK (water_quality IN ('good', 'saline', 'unknown')),
  climate_cell_id TEXT,
  profile_status TEXT DEFAULT 'pending' CHECK (profile_status IN ('pending', 'building', 'ready', 'failed')),
  profile_meta TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS crops (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  name_ml TEXT,
  family TEXT NOT NULL,
  duration_days INTEGER NOT NULL,
  need_mm INTEGER NOT NULL,
  water_need TEXT NOT NULL,
  drought_tol TEXT NOT NULL CHECK (drought_tol IN ('L', 'M', 'H')),
  waterlog_tol TEXT NOT NULL CHECK (waterlog_tol IN ('L', 'M', 'H')),
  n_effect TEXT NOT NULL CHECK (n_effect IN ('fixer', 'neutral', 'heavy')),
  ph_min REAL NOT NULL,
  ph_max REAL NOT NULL,
  t_min REAL NOT NULL,
  t_max REAL NOT NULL,
  t_flower_max REAL NOT NULL,
  flower_frac_start REAL NOT NULL,
  flower_frac_end REAL NOT NULL,
  start_windows TEXT NOT NULL,
  long_duration INTEGER DEFAULT 0,
  watch_for TEXT,
  elev_min REAL NOT NULL,
  elev_max REAL NOT NULL,
  repeat_penalty INTEGER NOT NULL,
  om_bonus INTEGER DEFAULT 0,
  erosion_cover INTEGER DEFAULT 0,
  market TEXT NOT NULL,
  salinity_tol TEXT NOT NULL CHECK (salinity_tol IN ('L', 'M', 'H')),
  good_next TEXT,
  source TEXT,
  source_date TEXT
);

CREATE TABLE IF NOT EXISTS field_crops (
  field_id INTEGER NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
  crop_id INTEGER NOT NULL REFERENCES crops(id) ON DELETE CASCADE,
  class TEXT NOT NULL CHECK (class IN ('suitable', 'marginal', 'not_suitable')),
  reason TEXT,
  start_windows TEXT,
  computed_at TEXT DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (field_id, crop_id)
);

CREATE TABLE IF NOT EXISTS seasons (
  id SERIAL PRIMARY KEY,
  field_id INTEGER NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
  crop_id INTEGER REFERENCES crops(id),
  status TEXT NOT NULL CHECK (status IN ('planned', 'active', 'completed')),
  start_date TEXT,
  end_date TEXT,
  outcome TEXT CHECK (outcome IN ('good', 'average', 'poor', 'failed', NULL)),
  loss_percent INTEGER,
  investment REAL,
  revenue REAL,
  suspected_cause TEXT,
  approval_status TEXT DEFAULT 'pending_review' CHECK (approval_status IN ('pending_review', 'approved', 'corrected')),
  approved_cause TEXT,
  approved_by INTEGER REFERENCES users(id),
  approver_role TEXT CHECK (approver_role IN ('farmer', 'mentor', 'officer', NULL)),
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS findings (
  id SERIAL PRIMARY KEY,
  season_id INTEGER NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  week_from INTEGER NOT NULL,
  week_to INTEGER NOT NULL,
  deviation REAL,
  unit TEXT,
  crop_stage TEXT,
  severity TEXT NOT NULL,
  confidence TEXT NOT NULL,
  source TEXT,
  resolution TEXT,
  text_plain TEXT,
  explainer_key TEXT,
  review_status TEXT DEFAULT 'pending' CHECK (review_status IN ('pending', 'confirmed', 'corrected', 'rejected'))
);

CREATE TABLE IF NOT EXISTS corrections (
  id SERIAL PRIMARY KEY,
  finding_id INTEGER REFERENCES findings(id) ON DELETE CASCADE,
  field_id INTEGER REFERENCES fields(id) ON DELETE CASCADE,
  corrected_by INTEGER NOT NULL REFERENCES users(id),
  by_role TEXT NOT NULL,
  new_cause TEXT,
  note TEXT,
  verified INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plans (
  id SERIAL PRIMARY KEY,
  field_id INTEGER NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
  mode TEXT NOT NULL CHECK (mode IN ('suggest', 'farmer_led')),
  start_week INTEGER NOT NULL,
  toggle TEXT,
  farmer_crop_id INTEGER REFERENCES crops(id),
  farmer_reason TEXT,
  scenario_json TEXT NOT NULL,
  outlook_json TEXT NOT NULL,
  weights_json TEXT NOT NULL,
  inputs_json TEXT,
  chosen_card_id INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plan_cards (
  id SERIAL PRIMARY KEY,
  plan_id INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  is_existing_rotation INTEGER DEFAULT 0,
  crop_id INTEGER REFERENCES crops(id),
  verdict TEXT NOT NULL,
  total REAL,
  factors_json TEXT NOT NULL,
  flags_json TEXT NOT NULL,
  confidence_json TEXT NOT NULL,
  evidence_json TEXT,
  notes_json TEXT,
  text_json TEXT,
  text_validated INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reports (
  id SERIAL PRIMARY KEY,
  plan_id INTEGER REFERENCES plans(id) ON DELETE CASCADE,
  created_by INTEGER NOT NULL REFERENCES users(id),
  share_token TEXT UNIQUE NOT NULL,
  shared_with INTEGER REFERENCES users(id),
  fields_shared TEXT NOT NULL,
  snapshot_json TEXT NOT NULL,
  status TEXT DEFAULT 'sent' CHECK (status IN ('sent', 'viewed', 'commented', 'revoked')),
  expires_at TEXT NOT NULL,
  revoked_at TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS report_comments (
  id SERIAL PRIMARY KEY,
  report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
  author_id INTEGER NOT NULL REFERENCES users(id),
  author_label TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  target_id INTEGER,
  status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'done', 'done_with_gaps', 'failed')),
  step TEXT,
  progress INTEGER DEFAULT 0,
  steps_json TEXT,
  error TEXT,
  result_json TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  action TEXT NOT NULL,
  object_type TEXT NOT NULL,
  object_id INTEGER,
  details_json TEXT,
  at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS climate_cells (
  id TEXT PRIMARY KEY,
  centroid_lat REAL NOT NULL,
  centroid_lon REAL NOT NULL,
  series_path TEXT NOT NULL,
  normals_path TEXT NOT NULL,
  sources_json TEXT,
  fetched_at TEXT,
  years_covered TEXT
);
