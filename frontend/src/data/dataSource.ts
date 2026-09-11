export type DataMode = "mock" | "api";

const envMode = import.meta.env.VITE_DATA_MODE as DataMode | undefined;

export const DATA_MODE: DataMode = envMode ?? "mock";

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

/** Must match the backend's API_KEY (see ../../.env.example at repo root). */
export const API_KEY: string = (import.meta.env.VITE_API_KEY as string | undefined) ?? "";

/** Simulated latency in mock mode so loading/entrance states are exercised. */
export const MOCK_LATENCY_MS = 260;