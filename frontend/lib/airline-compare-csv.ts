import type { CompareRow } from "@/lib/api";
import { formatFlightValue } from "@/lib/flight-fields";
import { buildCsv } from "@/lib/csv";

export function buildAirlineCompareCsv(
  rows: CompareRow[],
  slugs: string[],
  columnLabels: Record<string, string>,
  cabin: string
): string {
  const headers = [
    "airline_slug",
    "airline_name",
    "cabin_class",
    ...rows.map((row) => row.field_key),
  ];

  const dataRows = slugs.map((slug) => [
    slug,
    columnLabels[slug] ?? slug,
    cabin,
    ...rows.map((row) => formatFlightValue(row.values[slug])),
  ]);

  return buildCsv(headers, dataRows);
}
