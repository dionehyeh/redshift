import type { FieldItem, UserProfile } from "./types";

export const MOCK_USER: UserProfile = {
  id: 1,
  name: "Kerala Demo Farmer",
  role: "farmer",
  language: "en",
  contact: "+91 98765 43210",
  helper_type: null,
  market_toggle: "play_safe",
  default_share_consent: 1,
};

export const MOCK_FIELDS: FieldItem[] = [
  {
    id: 1,
    farmer_id: 1,
    name: "Kuttanad Demonstration Plot",
    lat: 9.5833,
    lon: 76.5167,
    area_ha: 1.2,
    water_source: "canal",
    water_quality: "good",
    profile_status: "ready",
    created_at: "2026-11-10T10:00:00Z",
  },
  {
    id: 2,
    farmer_id: 1,
    name: "Palakkad Paddy & Pulse Field",
    lat: 10.7867,
    lon: 76.6548,
    area_ha: 0.8,
    water_source: "borewell",
    water_quality: "good",
    profile_status: "ready",
    created_at: "2026-11-12T14:30:00Z",
  },
  {
    id: 3,
    farmer_id: 1,
    name: "Wayanad Highland Terrace",
    lat: 11.6854,
    lon: 76.132,
    area_ha: 0.5,
    water_source: "rainfed",
    water_quality: "good",
    profile_status: "building",
    created_at: "2026-11-13T09:15:00Z",
  },
];

export const MOCK_STRATEGY_CARDS = [
  {
    id: 1,
    card_type: "customary",
    crop: "Paddy (Uma)",
    name_ml: "ഉമ നെല്ല്",
    headline: "Traditional High-Yield Wet Paddy",
    suitability: "suitable",
    resilience_score: 74,
    expected_yield: "4.8 - 5.2 t/ha",
    water_demand: "High (Canal continuous flow)",
    key_advantages: ["High regional market demand", "Subsidized procurement support"],
    climate_risks: ["Susceptible to late monsoon unseasonal cloudbursts"],
    soil_compatibility: "Matches local pH 5.4 with liming practice",
  },
  {
    id: 2,
    card_type: "alternative_1",
    crop: "Cowpea (Kanakamani)",
    name_ml: "പയർ",
    headline: "Nitrogen-Fixing Climate Shield",
    suitability: "suitable",
    resilience_score: 89,
    expected_yield: "1.2 - 1.5 t/ha (High market value)",
    water_demand: "Low (Residual soil moisture)",
    key_advantages: ["Restores nitrogen naturally", "Drought tolerant in dry weeks"],
    climate_risks: ["Requires well-drained bunds if water table surges"],
    soil_compatibility: "Thrives in acid clay loam",
  },
  {
    id: 3,
    card_type: "alternative_2",
    crop: "Sesame (Thilak)",
    name_ml: "എള്ള്",
    headline: "Short Duration Summer Rotation",
    suitability: "marginal",
    resilience_score: 68,
    expected_yield: "600 - 800 kg/ha",
    water_demand: "Very Low",
    key_advantages: ["High cash return per quintal", "Minimal pest interventions"],
    climate_risks: ["Sensitive to waterlogging during early seedling germination"],
    soil_compatibility: "Requires raised bed cultivation",
  },
];

export function getMockResponse<T>(path: string): T | null {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;

  if (cleanPath === "/fields" || cleanPath === "/fields/") {
    return {
      items: MOCK_FIELDS.map(({ farmer_id, ...field }) => ({
        ...field,
        climate_cell_id: null,
      })),
      total: MOCK_FIELDS.length,
    } as unknown as T;
  }

  if (cleanPath === "/me" || cleanPath === "/me/prefs") {
    return MOCK_USER as unknown as T;
  }

  const fieldMatch = cleanPath.match(/^\/fields\/(\d+)$/);
  if (fieldMatch) {
    const id = parseInt(fieldMatch[1], 10);
    const field = MOCK_FIELDS.find((f) => f.id === id);
    if (!field) return null;
    return {
      ...field,
      gaps: [],
      climate_cell_id: null,
      profile: {
        elevation_m: { value: 4.0, source: "SRTM GL1", resolution: "30 m", confidence: "high" },
        flood_prone: { value: true, source: "SRTM + Historical Rain", confidence: "medium" },
        soil_ph: { value: 5.4, source: "Soil Health Card / KAU", confidence: "high" },
        drainage: { value: "poor", source: "Terrain Model", confidence: "medium" },
        water_source: { value: field.water_source, source: "Farmer profile", confidence: "high" },
        water_quality: { value: field.water_quality, source: "Farmer profile", confidence: "high" },
      },
    } as unknown as T;
  }

  if (cleanPath.includes("/feasible-crops")) {
    const fieldId = Number(cleanPath.match(/^\/fields\/(\d+)\//)?.[1]);
    const crops = [
      { crop_id: 1, crop_name: "Paddy (Uma)", name_ml: "ഉമ നെല്ല്", family: "grass", water_need: "high", class: "suitable", reason: "Ideal for low elevation wetland soil", start_windows: ["W22", "W23"], duration_days: 130, computed_at: null },
      { crop_id: 2, crop_name: "Cowpea", name_ml: "പയർ", family: "legume", water_need: "low", class: "suitable", reason: "Nitrogen-fixing pulse suited for summer residual moisture", start_windows: ["W4", "W5"], duration_days: 75, computed_at: null },
      { crop_id: 3, crop_name: "Sesame", name_ml: "എള്ള്", family: "oilseed", water_need: "low", class: "marginal", reason: "Sensitive to excess soil moisture during seedling stage", start_windows: ["W2"], duration_days: 90, computed_at: null },
      { crop_id: 4, crop_name: "Tea", name_ml: "തേയില", family: "shrub", water_need: "medium", class: "not_suitable", reason: "Elevation too low (< 800m required)", start_windows: [], duration_days: null, computed_at: null },
    ];
    return {
      field_id: fieldId,
      computed_at: null,
      suitable: crops.filter((crop) => crop.class === "suitable"),
      marginal: crops.filter((crop) => crop.class === "marginal"),
      not_suitable: crops.filter((crop) => crop.class === "not_suitable"),
    } as unknown as T;
  }

  if (cleanPath.includes("/history")) {
    const fieldId = Number(cleanPath.match(/^\/fields\/(\d+)\//)?.[1]);
    return {
      field_id: fieldId,
      total: 2,
      seasons: [
        {
          id: 1,
          field_id: fieldId,
          crop_id: 1,
          crop_name: "Paddy (Uma)",
          status: "completed",
          start_date: "2025-06-15",
          end_date: "2025-10-20",
          outcome: "good",
          loss_percent: null,
          suspected_cause: null,
          approval_status: "approved",
          approved_cause: "Adequate monsoon rainfall with minimal pest stress",
          approver_role: null,
          investment: null,
          revenue: null,
          created_at: "2025-10-20T00:00:00Z",
          name_ml: "ഉമ നെല്ല്",
          family: "grass",
          approved_by_name: null,
        },
        {
          id: 2,
          field_id: fieldId,
          crop_id: 2,
          crop_name: "Cowpea",
          status: "completed",
          start_date: "2025-11-01",
          end_date: "2026-01-15",
          outcome: "moderate",
          loss_percent: null,
          suspected_cause: null,
          approval_status: "approved",
          approved_cause: "Slight water deficit in late vegetative stage",
          approver_role: null,
          investment: null,
          revenue: null,
          created_at: "2026-01-15T00:00:00Z",
          name_ml: "പയർ",
          family: "legume",
          approved_by_name: null,
        },
      ],
    } as unknown as T;
  }

  const mapMatch = cleanPath.match(/^\/fields\/(\d+)\/map$/);
  if (mapMatch) {
    const field = MOCK_FIELDS.find((item) => item.id === Number(mapMatch[1]));
    if (!field) return null;
    return {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: [field.lon, field.lat] },
          properties: {
            name: field.name,
            elevation_m: 4,
            slope: "low",
            flood_prone: true,
            drainage: "poor",
            area_ha: field.area_ha,
            profile_status: field.profile_status,
          },
        },
      ],
    } as unknown as T;
  }

  if (cleanPath.includes("/plans")) {
    return {
      id: 1,
      field_id: 1,
      field_name: "Kuttanad Demonstration Plot",
      season: "puncha",
      chosen_card_id: 2,
      cards: MOCK_STRATEGY_CARDS,
      plan_id: 1,
    } as unknown as T;
  }

  if (cleanPath.includes("/seasons")) {
    return {
      id: 1,
      field_id: 1,
      crop_name: "Paddy (Uma)",
      start_date: "2025-06-15",
      end_date: "2025-10-20",
      outcome: "moderate",
      findings: [
        {
          id: 1,
          metric: "Precipitation Deficit (GPM IMERG)",
          finding: "-32% lower rain during vegetative tillering phase (Week 28-30)",
          severity: "warning",
        },
        {
          id: 2,
          metric: "Thermal Stress (NASA POWER)",
          finding: "Daytime surface temperatures exceeded 34.5°C threshold on 4 consecutive days",
          severity: "caution",
        },
      ],
      recommendations: [
        "Introduce short-duration pulse like Cowpea in rotation to break pest cycle and optimize residual soil moisture.",
      ],
    } as unknown as T;
  }

  if (cleanPath.includes("/timeline")) {
    const weeks = Array.from({ length: 52 }, (_, i) => i + 1);
    const rainNormals = weeks.map((w) => (w >= 22 && w <= 36 ? 80 + Math.sin(w) * 35 : 12 + Math.random() * 8));
    const rainObserved = rainNormals.map((r, i) => (i >= 25 && i <= 29 ? r * 0.65 : r * (0.9 + Math.random() * 0.2)));
    const tempNormals = weeks.map((w) => 27 + Math.sin((w / 52) * Math.PI) * 5);
    const tempObserved = tempNormals.map((t) => t + (Math.random() * 1.5 - 0.5));
    const ndviObserved = weeks.map((w) => (w >= 24 && w <= 42 ? 0.68 + Math.sin(w) * 0.12 : 0.35 + Math.random() * 0.08));

    return {
      weeks,
      source_note: "NASA POWER Daily (0.5° resolution) + GPM IMERG Final precipitation baselines (20-year climatology)",
      series: {
        rain_mm: {
          values: rainObserved,
          source: "GPM IMERG Late Run v06",
          resolution: "10 km (0.1°)",
          is_normal: false,
        },
        tmean: {
          values: tempObserved,
          source: "NASA POWER Thermal",
          resolution: "50 km (0.5°)",
          is_normal: false,
        },
        ndvi: {
          values: ndviObserved,
          source: "MODIS MOD13Q1 16-Day",
          resolution: "250 m",
          is_normal: false,
        },
      },
      normals: {
        rain_mm: rainNormals,
        tmean: tempNormals,
        ndvi: ndviObserved.map((n) => n * 0.95),
      },
    } as unknown as T;
  }

  if (cleanPath.includes("/map")) {
    return {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: {
            type: "Polygon",
            coordinates: [
              [
                [76.514, 9.581],
                [76.519, 9.581],
                [76.519, 9.585],
                [76.514, 9.585],
                [76.514, 9.581],
              ],
            ],
          },
          properties: {
            name: "Plot Boundary",
            area_ha: 1.2,
            flood_prone: true,
          },
        },
      ],
    } as unknown as T;
  }

  if (cleanPath === "/mentor/inbox") {
    return {
      items: [
        {
          report_id: 1,
          farmer_name: "Kerala Demo Farmer",
          created_at: "2026-11-14T08:00:00Z",
          status: "sent",
          expires_at: "2026-11-28T08:00:00Z",
        },
      ],
    } as unknown as T;
  }

  if (cleanPath.startsWith("/helpers")) {
    const helperType = new URLSearchParams(cleanPath.split("?")[1] ?? "").get("type");
    const helpers = [
      { id: 2, name: "Anjali Menon", role: "mentor", helper_type: "student", label: "Anjali Menon (student)" },
      { id: 3, name: "Dr. Radhakrishnan", role: "officer", helper_type: "officer", label: "Dr. Radhakrishnan (officer)" },
    ];
    return {
      items: helperType
        ? helpers.filter((helper) => helper.helper_type === helperType)
        : helpers,
    } as unknown as T;
  }

  if (/^\/reports\/\d+$/.test(cleanPath)) {
    return {
      id: 1,
      status: "sent",
      share_token: "mock-share-token",
      shared_fields: ["cards", "findings"],
      snapshot: {
        cards: [{ position: 1, crop: "paddy", verdict: "Feasible", total: 82 }],
        findings: [],
      },
      expires_at: "2026-11-28T08:00:00Z",
      revoked_at: null,
      comments: [
        { id: 1, author_label: "Agricultural Extension Officer", body: "Consider soil test results before applying amendments.", created_at: "2026-11-14T08:00:00Z" },
      ],
      created_at: "2026-11-14T08:00:00Z",
    } as unknown as T;
  }

  if (cleanPath === "/crops") {
    return {
      items: [
        { id: "paddy", name: { en: "Paddy", ml: "" }, family: "grass", duration_days: 130, water_need: "high", market: "high" },
        { id: "green_gram", name: { en: "Green Gram", ml: "" }, family: "legume", duration_days: 70, water_need: "low", market: "medium" },
        { id: "cowpea", name: { en: "Cowpea", ml: "" }, family: "legume", duration_days: 75, water_need: "low", market: "medium" },
        { id: "sesame", name: { en: "Sesame", ml: "" }, family: "oilseed", duration_days: 90, water_need: "low", market: "medium" },
      ],
    } as unknown as T;
  }

  if (cleanPath === "/reference/seasons") {
    return {
      seasons: [
        { key: "virippu", name: { en: "Virippu (Autumn)", ml: "വിരിപ്പ്" }, start_week: 18, end_week: 38, description: "Southwest monsoon crop cycle" },
        { key: "mundakan", name: { en: "Mundakan (Winter)", ml: "മുണ്ടകൻ" }, start_week: 38, end_week: 3, description: "Northeast monsoon crop cycle" },
        { key: "puncha", name: { en: "Puncha (Summer)", ml: "പുഞ്ച" }, start_week: 2, end_week: 16, description: "Summer / residual moisture crop cycle" },
      ],
    } as unknown as T;
  }

  if (cleanPath === "/sources") {
    return {
      items: [
        { name: "NASA POWER", used_for: "Temperature and climatological normals", resolution: "~50 km", latency: "Near Real-Time", limits: "Coarse spatial resolution." },
        { name: "GPM IMERG", used_for: "Precipitation estimates and dry spells", resolution: "~10 km", latency: "Final run ~3.5 months", limits: "May miss localized rainfall." },
      ],
    } as unknown as T;
  }

  return { field_id: 1, plan_id: 1, id: 1, success: true } as unknown as T;
}
