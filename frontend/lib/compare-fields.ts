/** Field metadata for compare view editing (mirrors shared/compare_fields.py). */

export type FieldType = "string" | "int" | "float" | "bool";

export const AIRCRAFT_FIELDS = [
  "aircraft_type_displayed",
  "aircraft_code_displayed",
  "configuration",
  "total_seats",
  "fleet_count",
  "manufacturer",
  "haul_type",
  "ife_provider",
  "ife_system_name",
  "wifi_provider",
  "wifi_system_name",
] as const;

export const CABIN_FIELDS = [
  "num_seats",
  "rows",
  "layout",
  "seat_manufacturer",
  "pitch_inch",
  "width_inch",
  "recline_inch",
  "recline_deg",
  "has_flat_bed",
  "screen_size_inch",
  "power_v",
  "usb_a_count",
  "usb_c_count",
  "direct_aisle_access_pct",
  "wireless_charging",
  "bluetooth_connectivity",
] as const;

export const FIELD_TYPES: Record<string, FieldType> = {
  aircraft_type_displayed: "string",
  aircraft_code_displayed: "string",
  configuration: "string",
  total_seats: "int",
  fleet_count: "int",
  manufacturer: "string",
  haul_type: "string",
  ife_provider: "string",
  ife_system_name: "string",
  wifi_provider: "string",
  wifi_system_name: "string",
  num_seats: "int",
  rows: "string",
  layout: "string",
  seat_manufacturer: "string",
  pitch_inch: "float",
  width_inch: "float",
  recline_inch: "float",
  recline_deg: "float",
  has_flat_bed: "bool",
  screen_size_inch: "float",
  power_v: "int",
  usb_a_count: "int",
  usb_c_count: "int",
  direct_aisle_access_pct: "int",
  wireless_charging: "string",
  bluetooth_connectivity: "string",
};

export function formatCompareValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export function getFieldType(fieldKey: string): FieldType {
  return FIELD_TYPES[fieldKey] ?? "string";
}

export function parseFieldInput(
  fieldKey: string,
  raw: string
): string | number | boolean | null {
  const fieldType = getFieldType(fieldKey);
  if (raw.trim() === "") {
    return fieldType === "bool" ? false : null;
  }
  if (fieldType === "bool") {
    const normalized = raw.trim().toLowerCase();
    if (normalized === "yes" || normalized === "true") return true;
    if (normalized === "no" || normalized === "false") return false;
    return raw === "1";
  }
  if (fieldType === "int") return parseInt(raw, 10);
  if (fieldType === "float") return parseFloat(raw);
  return raw;
}

export function serializeFieldInput(fieldKey: string, value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

export function valuesEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (a === null || a === undefined) return b === null || b === undefined;
  if (b === null || b === undefined) return false;
  return String(a) === String(b);
}
