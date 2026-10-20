/**
 * api.ts
 * ------
 * Everything the dashboard needs to talk to the FastAPI backend:
 * the data types (they match backend/app/schemas.py) and small fetch helpers.
 *
 * The backend address can be changed with NEXT_PUBLIC_API_URL in frontend/.env.local.
 */

export type Source = "simulated" | "sensor" | "nasa";
export type Status = "normal" | "warning" | "critical";

/** One stored measurement, as returned by the backend (ReadingOut). */
export interface Reading {
  id: number;
  timestamp: string; // ISO 8601, UTC
  source: Source;
  device_id: string | null;
  voltage_v: number;
  current_a: number; // negative = discharge
  temperature_c: number | null;
  soh_pct: number | null;
  soh_valid: boolean;
  soh_note: string | null;
  status: Status;
  alert_message: string | null;
}

/** One device that has sent readings (GET /devices). */
export interface Device {
  source: Source;
  device_id: string | null;
  readings: number;
  last_seen: string;
  last_status: Status;
}

export interface StatusOut {
  has_data: boolean;
  total_readings: number;
  latest: Reading | null;
}

export interface Health {
  status: "ok" | "degraded";
  service: string;
  version: string;
  database: string;
  database_file: string;
  soh_model: "loaded" | "not available";
  live_clients: number;
  server_time_utc: string;
}

export interface Thresholds {
  voltage_low_warning_v: number;
  voltage_low_critical_v: number;
  voltage_high_warning_v: number;
  voltage_high_critical_v: number;
  temperature_high_warning_c: number;
  temperature_high_critical_c: number;
  temperature_low_warning_c: number;
  current_warning_a: number;
  current_critical_a: number;
  note: string;
}

export interface ModelInfo {
  available: boolean;
  problem: string | null;
  warning: string | null;
  model_type: string | null;
  target_definition: string | null;
  feature_window_s: number | null;
  feature_columns: string[];
  trained_on_cells: string[];
  lobo_overall_metrics: { mae: number; rmse: number; r2: number } | null;
  valid_for: string | null;
}

/** The 8 early-discharge features the SoH model needs (see model/scripts/build_features.py). */
export interface SohFeatures {
  v_start_v: number;
  v_drop_30s_v: number;
  v_at_60s_v: number;
  v_at_300s_v: number;
  v_at_600s_v: number;
  v_slope_60_600_mv_per_min: number;
  temp_start_c: number;
  temp_rise_600s_c: number;
}

export interface SohPrediction {
  soh_pct: number | null;
  soh_valid: boolean;
  soh_note: string;
  out_of_range: string[];
}

/** A real NASA row: cell B0005, discharge cycle 1 (measured SoH 92.82 % of rated 2.0 Ah). */
export const NASA_EXAMPLE = {
  cell: "B0005",
  cycle: 1,
  measuredSohPct: 92.82,
  features: {
    v_start_v: 4.1915,
    v_drop_30s_v: 0.1516,
    v_at_60s_v: 3.9458,
    v_at_300s_v: 3.8289,
    v_at_600s_v: 3.7495,
    v_slope_60_600_mv_per_min: -19.386,
    temp_start_c: 24.33,
    temp_rise_600s_c: 5.0745,
  } satisfies SohFeatures,
};

/** One measured discharge (GET /capacity, see backend/app/services/capacity.py). */
export interface DischargeRun {
  start: string;
  end: string;
  duration_s: number;
  readings: number;
  rest_voltage_v: number | null;
  start_voltage_v: number;
  end_voltage_v: number;
  capacity_mah: number;
  energy_wh: number;
  mean_current_a: number;
  max_temperature_c: number | null;
  temperature_rise_c: number | null;
  ended: "cutoff" | "stopped_early" | "data_gap" | "in_progress";
  started_full: boolean;
  soh_pct: number | null;
  soh_note: string;
  warnings: string[];
}

export interface Capacity {
  source: Source;
  device_id: string | null;
  available: boolean;
  note: string;
  rated_capacity_mah: number;
  cutoff_v: number;
  full_rest_v: number;
  runs: DischargeRun[];
}

/** Messages pushed by the backend over the WebSocket (see backend/app/live_api.py). */
export type LiveMessage =
  | { type: "hello"; message: string; clients: number }
  | { type: "reading"; data: Reading };

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
export const WS_URL = API_URL.replace(/^http/, "ws") + "/ws";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(API_URL + path, { cache: "no-store", ...init });
  } catch {
    throw new Error(`Backend not reachable at ${API_URL}. Is uvicorn running?`);
  }
  if (!response.ok) {
    throw new Error(`${path} returned HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => request<Health>("/health"),
  status: () => request<StatusOut>("/status"),
  devices: () => request<Device[]>("/devices"),
  history: (limit = 120, filter: { source?: Source; deviceId?: string | null } = {}) => {
    const query = new URLSearchParams({ limit: String(limit) });
    if (filter.source) query.set("source", filter.source);
    if (filter.deviceId) query.set("device_id", filter.deviceId);
    return request<Reading[]>(`/history?${query.toString()}`);
  },
  thresholds: () => request<Thresholds>("/thresholds"),
  capacity: (source: Source, deviceId: string | null) => {
    const query = new URLSearchParams({ source });
    if (deviceId) query.set("device_id", deviceId);
    return request<Capacity>(`/capacity?${query.toString()}`);
  },
  modelInfo: () => request<ModelInfo>("/soh/model-info"),
  predictSoh: (features: SohFeatures) =>
    request<SohPrediction>("/soh/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(features),
    }),
};
