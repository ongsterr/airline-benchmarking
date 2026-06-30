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
  category: string;
  values: Record<string, string | number | boolean | null>;
};

async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { next: { revalidate: 60 } });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`);
  }
  return res.json();
}

export async function getAirlineSummaries(): Promise<AirlineSummary[]> {
  return fetchApi("/api/v1/airlines/summary");
}

export async function getAircraftList(params?: {
  airline?: string;
  aircraft_type?: string;
  search?: string;
}): Promise<{ items: AircraftListItem[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.airline) query.set("airline", params.airline);
  if (params?.aircraft_type) query.set("aircraft_type", params.aircraft_type);
  if (params?.search) query.set("search", params.search);
  const qs = query.toString();
  return fetchApi(`/api/v1/aircraft${qs ? `?${qs}` : ""}`);
}

export async function getCompare(
  ids: string[],
  cabin?: string
): Promise<CompareRow[]> {
  const query = new URLSearchParams({ ids: ids.join(",") });
  if (cabin) query.set("cabin", cabin);
  return fetchApi(`/api/v1/compare?${query}`);
}
