/** Flight feature display helpers (mirrors shared/flight_fields.py). */

export const FLIGHT_FIELDS = [
  "check_in_priority",
  "cabin_bag_pieces",
  "cabin_bag_kg_per_piece",
  "cabin_bag_kg_total",
  "checked_bag_pieces",
  "checked_bag_kg_per_piece",
  "checked_bag_kg_total",
  "boarding_priority",
  "lounge_access",
  "amenity_kit",
  "amenity_kit_brand",
] as const;

export function formatFlightValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) {
    if (value.length === 0) return "—";
    return value.map(String).join(", ");
  }
  return String(value);
}

export function flightFieldLabel(fieldKey: string): string {
  return fieldKey.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
