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

export function getMockResponse<T>(path: string): T | null {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;

  if (cleanPath === "/fields" || cleanPath === "/fields/") {
    return { items: MOCK_FIELDS, next_cursor: null } as unknown as T;
  }

  if (cleanPath === "/me") {
    return MOCK_USER as unknown as T;
  }

  const fieldMatch = cleanPath.match(/^\/fields\/(\d+)$/);
  if (fieldMatch) {
    const id = parseInt(fieldMatch[1], 10);
    const field = MOCK_FIELDS.find((f) => f.id === id) || MOCK_FIELDS[0];
    return {
      ...field,
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
    return {
      crops: [
        { crop: "Paddy (Uma)", name_ml: "ഉമ നെല്ല്", class: "suitable", reason: "Ideal for low elevation wetland soil", start_windows: ["W22", "W23"] },
        { crop: "Cowpea", name_ml: "പയർ", class: "suitable", reason: "Nitrogen-fixing pulse suited for summer residual moisture", start_windows: ["W4", "W5"] },
        { crop: "Sesame", name_ml: "എള്ള്", class: "marginal", reason: "Sensitive to excess soil moisture during seedling stage", start_windows: ["W2"] },
        { crop: "Tea", name_ml: "തേയില", class: "not_suitable", reason: "Elevation too low (< 800m required)", start_windows: [] },
      ],
    } as unknown as T;
  }

  return null;
}
