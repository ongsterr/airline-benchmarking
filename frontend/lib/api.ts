const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  last_pipeline_update: string | null;
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

export type CompareRow = {
  feature: string;
  field_key: string;
  scope: "aircraft" | "cabin";
  category: string;
  values: Record<string, string | number | boolean | null>;
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

export type AircraftConfigUpdate = {
  aircraft?: Record<string, string | number | boolean | null>;
  cabins?: Record<string, Record<string, string | number | boolean | null>>;
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
  return fetchApi("/api/v1/airlines/summary");
}

export async function getAircraftList(params?: {
  airline?: string | string[];
  aircraft_type?: string | string[];
  search?: string;
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
  if (params?.search) query.set("search", params.search);
  const qs = query.toString();
  return fetchApi(`/api/v1/aircraft${qs ? `?${qs}` : ""}`);
}

export async function getCompare(
  ids: string[],
  cabin?: string
): Promise<CompareResponse> {
  const query = new URLSearchParams({ ids: ids.join(",") });
  if (cabin) query.set("cabin", cabin);
  return fetchApi(`/api/v1/compare?${query}`);
}

export async function updateAircraftConfig(
  svgId: string,
  body: AircraftConfigUpdate
): Promise<void> {
  await fetchApi(`/api/v1/aircraft/${encodeURIComponent(svgId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
}
