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

/** Messages pushed by the backend over the WebSocket (see backend/app/live_api.py). */
export type LiveMessage =
  | { type: "hello"; message: string; clients: number }
  | { type: "reading"; data: Reading };

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
export const WS_URL = API_URL.replace(/^http/, "ws") + "/ws";

async function getJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(API_URL + path, { cache: "no-store" });
  } catch {
    throw new Error(`Backend not reachable at ${API_URL}. Is uvicorn running?`);
  }
  if (!response.ok) {
    throw new Error(`${path} returned HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => getJson<Health>("/health"),
  status: () => getJson<StatusOut>("/status"),
  history: (limit = 120, source?: Source) =>
    getJson<Reading[]>(`/history?limit=${limit}${source ? `&source=${source}` : ""}`),
  thresholds: () => getJson<Thresholds>("/thresholds"),
  modelInfo: () => getJson<ModelInfo>("/soh/model-info"),
};