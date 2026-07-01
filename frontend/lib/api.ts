import { isDisplayAirlineSlug } from "@/lib/constants";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const EDIT_AUTH_TOKEN_KEY = "edit_auth_token";

export function getEditAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(EDIT_AUTH_TOKEN_KEY);
}

export function setEditAuthToken(token: string): void {
  sessionStorage.setItem(EDIT_AUTH_TOKEN_KEY, token);
}

export function clearEditAuthToken(): void {
  sessionStorage.removeItem(EDIT_AUTH_TOKEN_KEY);
}

function authHeaders(): HeadersInit {
  const token = getEditAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export type SeatCounts = {
  first: number;
  business: number;
  premium_economy: number;
  economy: number;
  total: number;
};

export type AirlineSummary = {
  slug: string;
  iata_code: string | null;
  name: string;
  config_count: number;
  total_fleet_seats: number;
  aircraft_types: string[];
  long_haul_count: number;
  short_haul_count: number;
  airbus_count: number;
  boeing_count: number;
  other_aircraft_count: number;
  last_pipeline_update: string | null;
};

export type AircraftFilterOptions = {
  haul_types: string[];
  manufacturers: string[];
};

export type AircraftListItem = {
  svg_id: string;
  airline_slug: string;
  airline_name: string;
  is_dual_deck?: boolean;
  aircraft_type_displayed: string | null;
  aircraft_code_displayed: string | null;
  configuration: string | null;
  total_seats: number | null;
  seat_counts: SeatCounts | null;
  source_url: string;
  last_updated: string | null;
};

export type FlightSourceCandidate = {
  url: string;
  cabin_keys?: string[];
  page_type?: string;
  title?: string | null;
  source_type?: string;
};

export type CompareRow = {
  feature: string;
  field_key: string;
  scope: "aircraft" | "cabin" | "flight";
  category: string;
  values: Record<string, string | number | boolean | FlightSourceCandidate[] | null>;
};

export type CompareConfigColumn = {
  svg_id: string;
  airline_slug: string;
  airline_name: string;
  aircraft_type_displayed: string | null;
  aircraft_code_displayed: string | null;
  configuration: string | null;
  source_url: string;
};

export type CompareResponse = {
  columns: CompareConfigColumn[];
  rows: CompareRow[];
};

export type CabinFlightFeatures = {
  cabin_class: string;
  check_in_priority: string | null;
  cabin_bag_pieces: number | null;
  cabin_bag_kg_per_piece: number | null;
  cabin_bag_kg_total: number | null;
  checked_bag_pieces: number | null;
  checked_bag_kg_per_piece: number | null;
  checked_bag_kg_total: number | null;
  boarding_priority: string | null;
  lounge_access: string | null;
  amenity_kit: string[] | null;
  amenity_kit_brand: string | null;
  extra_features?: Record<string, unknown>;
};

export type AirlineFlightFeatures = {
  cabins: Record<string, CabinFlightFeatures>;
};

export type AircraftDetail = AircraftListItem & {
  svg_id: string;
  airline_iata: string;
  airline_name: string;
  aircraft_type: string | null;
  description: string | null;
  ife_provider: string | null;
  ife_system_name: string | null;
  wifi_provider: string | null;
  wifi_system_name: string | null;
  cabins: Record<
    string,
    {
      cabin_class: string;
      num_seats: number;
      layout: string | null;
      pitch_inch: number | null;
      width_inch: number | null;
      seat_manufacturer: string | null;
      has_flat_bed: boolean;
      [key: string]: unknown;
    }
  >;
  flight_features: AirlineFlightFeatures | null;
  source_url?: string;
};

export type CompareAirlineColumn = {
  slug: string;
  iata_code: string | null;
  name: string;
};

export type CompareAirlineResponse = {
  columns: CompareAirlineColumn[];
  rows: CompareRow[];
};

export type AircraftConfigUpdate = {
  aircraft?: Record<string, string | number | boolean | null>;
  cabins?: Record<string, Record<string, string | number | boolean | null>>;
};

export type AirlineFlightFeaturesUpdate = {
  fields: Record<string, string | number | string[] | null>;
  source_url?: string | null;
};

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    next: init?.method ? undefined : { revalidate: 60 },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body || path}`);
  }
  return res.json();
}

export async function getAirlineSummaries(): Promise<AirlineSummary[]> {
  const summaries: AirlineSummary[] = await fetchApi("/api/v1/airlines/summary");
  return summaries.filter((summary) => isDisplayAirlineSlug(summary.slug));
}

export async function getAircraftFilterOptions(): Promise<AircraftFilterOptions> {
  return fetchApi("/api/v1/aircraft/filter-options");
}

export async function getAircraftList(params?: {
  airline?: string | string[];
  aircraft_type?: string | string[];
  haul_type?: string | string[];
  manufacturer?: string | string[];
  search?: string;
  has_premium_economy?: boolean;
  offset?: number;
  limit?: number;
}): Promise<{ items: AircraftListItem[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.airline) {
    const value = Array.isArray(params.airline)
      ? params.airline.join(",")
      : params.airline;
    if (value) query.set("airline", value);
  }
  if (params?.aircraft_type) {
    const value = Array.isArray(params.aircraft_type)
      ? params.aircraft_type.join(",")
      : params.aircraft_type;
    if (value) query.set("aircraft_type", value);
  }
  if (params?.haul_type) {
    const value = Array.isArray(params.haul_type)
      ? params.haul_type.join(",")
      : params.haul_type;
    if (value) query.set("haul_type", value);
  }
  if (params?.manufacturer) {
    const value = Array.isArray(params.manufacturer)
      ? params.manufacturer.join(",")
      : params.manufacturer;
    if (value) query.set("manufacturer", value);
  }
  if (params?.search) query.set("search", params.search);
  if (params?.has_premium_economy) {
    query.set("has_premium_economy", "true");
  }
  if (params?.offset !== undefined) {
    query.set("offset", String(params.offset));
  }
  if (params?.limit !== undefined) {
    query.set("limit", String(params.limit));
  }
  const qs = query.toString();
  return fetchApi(`/api/v1/aircraft${qs ? `?${qs}` : ""}`);
}

export async function loginForEdit(password: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(
      res.status === 401
        ? "Invalid password"
        : `Login failed ${res.status}: ${body || "unknown error"}`
    );
  }
  const data = (await res.json()) as { token: string };
  setEditAuthToken(data.token);
}

export async function getEditAuthStatus(): Promise<boolean> {
  const res = await fetch(`${API_URL}/api/v1/auth/me`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) {
    return false;
  }
  const data = (await res.json()) as { authenticated: boolean };
  return data.authenticated;
}

export async function logoutForEdit(): Promise<void> {
  clearEditAuthToken();
  try {
    await fetch(`${API_URL}/api/v1/auth/logout`, { method: "POST", cache: "no-store" });
  } catch {
    // Best-effort; client token is already cleared.
  }
}

export async function getCompare(
  ids: string[],
  cabin?: string
): Promise<CompareResponse> {
  const query = new URLSearchParams({ ids: ids.join(",") });
  if (cabin) query.set("cabin", cabin);
  return fetchApi(`/api/v1/compare?${query}`);
}

export async function getAircraftDetail(svgId: string): Promise<AircraftDetail> {
  return fetchApi(`/api/v1/aircraft/${encodeURIComponent(svgId)}`);
}

export async function getAirlineCompare(
  slugs: string[],
  cabin?: string
): Promise<CompareAirlineResponse> {
  const query = new URLSearchParams({ slugs: slugs.join(",") });
  if (cabin) query.set("cabin", cabin);
  return fetchApi(`/api/v1/compare/airlines?${query}`);
}

export async function updateAirlineFlightFeatures(
  slug: string,
  cabin: string,
  body: AirlineFlightFeaturesUpdate
): Promise<void> {
  const query = new URLSearchParams({ cabin });
  await fetchApi(
    `/api/v1/airlines/${encodeURIComponent(slug)}/flight-features?${query}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify(body),
      cache: "no-store",
    }
  );
}

export async function updateAircraftConfig(
  svgId: string,
  body: AircraftConfigUpdate
): Promise<void> {
  await fetchApi(`/api/v1/aircraft/${encodeURIComponent(svgId)}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
}

export async function downloadFleetCsv(ids: string[]): Promise<void> {
  if (ids.length === 0) return;
  const query = new URLSearchParams({ ids: ids.join(",") });
  const res = await fetch(`${API_URL}/api/v1/export.csv?${query.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body || "download csv failed"}`);
  }

  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") || "";
  const fileNameMatch = disposition.match(/filename="([^"]+)"/i);
  const filename = fileNameMatch?.[1] || "fleet-export.csv";
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export type PipelineType = "hardware" | "flight";
export type PipelineRunStatus = "running" | "completed" | "failed";

export type PipelineRun = {
  id: string;
  pipeline_type: PipelineType;
  status: PipelineRunStatus;
  started_at: string;
  finished_at: string | null;
  airlines: string[];
  configs_discovered: number;
  configs_updated: number;
  configs_skipped: number;
  errors: string[] | null;
};

export type PipelineTriggerOptions = {
  airlines: string[];
  force?: boolean;
  skipExisting?: boolean;
};

async function pipelineFetchApi<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...authHeaders(),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body || "request failed"}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

function pipelineTriggerBody(options: PipelineTriggerOptions) {
  return {
    airlines: options.airlines,
    force: options.force ?? false,
    skip_existing: options.skipExisting ?? false,
  };
}

export async function triggerHardwarePipeline(
  options: PipelineTriggerOptions
): Promise<PipelineRun> {
  return pipelineFetchApi<PipelineRun>("/api/v1/pipeline/hardware", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(pipelineTriggerBody(options)),
  });
}

export async function triggerFlightPipeline(
  options: PipelineTriggerOptions
): Promise<PipelineRun> {
  return pipelineFetchApi<PipelineRun>("/api/v1/pipeline/flight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(pipelineTriggerBody(options)),
  });
}

export async function getPipelineRun(runId: string): Promise<PipelineRun> {
  return pipelineFetchApi<PipelineRun>(
    `/api/v1/pipeline/runs/${encodeURIComponent(runId)}`
  );
}

export async function getActivePipelineRun(): Promise<PipelineRun | null> {
  return pipelineFetchApi<PipelineRun | null>("/api/v1/pipeline/runs/active");
}
