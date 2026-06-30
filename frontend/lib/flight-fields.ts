/** Flight feature display and edit helpers (mirrors shared/flight_fields.py). */

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

export type FlightFieldType = "string" | "int" | "list";

export const FLIGHT_FIELD_TYPES: Record<string, FlightFieldType> = {
  check_in_priority: "string",
  cabin_bag_pieces: "int",
  cabin_bag_kg_per_piece: "int",
  cabin_bag_kg_total: "int",
  checked_bag_pieces: "int",
  checked_bag_kg_per_piece: "int",
  checked_bag_kg_total: "int",
  boarding_priority: "string",
  lounge_access: "string",
  amenity_kit: "list",
  amenity_kit_brand: "string",
  source_url: "string",
};

export function formatFlightValue(value: unknown): string {
  if (value === null || value === undefined || value === "—") return "—";
  if (Array.isArray(value)) {
    if (value.length === 0) return "—";
    return value.map(String).join(", ");
  }
  return String(value);
}

export function flightFieldLabel(fieldKey: string): string {
  if (fieldKey === "source_url") return "Reference URL";
  return fieldKey.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function getFlightFieldType(fieldKey: string): FlightFieldType {
  return FLIGHT_FIELD_TYPES[fieldKey] ?? "string";
}

export function parseFlightFieldInput(fieldKey: string, raw: string): unknown {
  const fieldType = getFlightFieldType(fieldKey);
  if (raw.trim() === "") return null;
  if (fieldType === "int") return parseInt(raw, 10);
  if (fieldType === "list") {
    return raw
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean);
  }
  return raw;
}

export function serializeFlightFieldInput(fieldKey: string, value: unknown): string {
  if (value === null || value === undefined || value === "—") return "";
  if (Array.isArray(value)) return value.map(String).join(", ");
  return String(value);
}

export function isDisplayableUrl(value: unknown): value is string {
  if (typeof value !== "string" || value === "—") return false;
  return value.startsWith("http://") || value.startsWith("https://");
}

export function flightValuesEqual(
  fieldKey: string,
  a: unknown,
  b: unknown
): boolean {
  if (getFlightFieldType(fieldKey) === "list") {
    return (
      serializeFlightFieldInput(fieldKey, a) === serializeFlightFieldInput(fieldKey, b)
    );
  }
  if (a === b) return true;
  if (a === null || a === undefined || a === "—") {
    return b === null || b === undefined || b === "—";
  }
  if (b === null || b === undefined || b === "—") return false;
  return String(a) === String(b);
}
