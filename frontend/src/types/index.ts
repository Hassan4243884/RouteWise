// ─────────────────────────────────────────────────────────────────────────────
// Shared TypeScript types — mirrors the Django API response exactly
// ─────────────────────────────────────────────────────────────────────────────

export type RiskLevel = 'low' | 'moderate' | 'high' | 'severe' | 'no_travel';
export type CheckpointInterval = 10 | 25 | 50;
export type AppStatus = 'idle' | 'loading' | 'success' | 'error';

// ── Weather & checkpoint ─────────────────────────────────────────────────────

export interface WeatherData {
  wind_speed_mph: number;
  rain_in_hr: number;
  snow_in_hr: number;
  temperature_f: number;
  weather_code: number;
}

export interface Checkpoint {
  index: number;
  lat: number;
  lng: number;
  distance_from_start_miles: number;
  eta: string;              // ISO datetime string
  weather: WeatherData;
  risk_level: RiskLevel;
}

// ── Route ────────────────────────────────────────────────────────────────────

export interface RouteSummary {
  distance_miles: number;
  duration_minutes: number;
  low_miles: number;
  moderate_miles: number;
  high_miles: number;
  severe_miles: number;
  no_travel_miles: number;
  worst_risk: RiskLevel;
  avg_risk_score: number;
  rank: number;
}

export interface RouteResult {
  id: string;
  label: string;
  summary: RouteSummary;
  /** Ordered list of [lat, lng] pairs from the backend */
  polyline: [number, number][];
  checkpoints: Checkpoint[];
}

export interface RoutesResponse {
  recommended_route_id: string;
  routes: RouteResult[];
}

// ── Heatmap ──────────────────────────────────────────────────────────────────

export interface HeatmapPoint {
  lat: number;
  lng: number;
  intensity: number;  // 0.0 – 1.0
}

export interface HeatmapFrame {
  hour_offset: number;
  points: HeatmapPoint[];
}

export interface HeatmapResponse {
  frames: HeatmapFrame[];
}

// ── Form input ───────────────────────────────────────────────────────────────

export interface RouteFormInput {
  origin: string;
  destination: string;
  departure_time: string;   // ISO datetime string
  load_weight_lbs: number;
  checkpoint_interval_miles: CheckpointInterval;
}

// ── UI state ─────────────────────────────────────────────────────────────────

export interface HoverInfo {
  x: number;
  y: number;
  checkpoint: Checkpoint;
}
