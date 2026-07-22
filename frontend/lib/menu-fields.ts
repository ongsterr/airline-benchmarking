import type { MenuCompareItemDetail, MenuMetricCounts } from "@/lib/api";

export const MENU_ITEM_TYPE_OPTIONS = [
  { value: "all", label: "All items" },
  { value: "food", label: "Food" },
  { value: "beverage", label: "Beverage" },
] as const;

export const MENU_SUMMARY_METRICS = [
  { key: "alcoholic", label: "Alcoholic" },
  { key: "non_alcoholic", label: "Non-alcoholic" },
  { key: "vegetarian", label: "Vegetarian" },
  { key: "vegan", label: "Vegan" },
  { key: "localized", label: "Localised" },
] as const;

export type MenuSummaryMetricKey = (typeof MENU_SUMMARY_METRICS)[number]["key"];

export function formatMenuServiceDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  if (!year || !month || !day) return isoDate;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

export function formatMenuFlightLabel(option: {
  flight_number: string;
  origin_iata: string;
  dest_iata: string;
  service_date: string;
}): string {
  return `EK ${option.flight_number} ${option.origin_iata}→${option.dest_iata} ${formatMenuServiceDate(option.service_date)}`;
}

export function emptyMetricCounts(): MenuMetricCounts {
  return {
    alcoholic: 0,
    non_alcoholic: 0,
    vegetarian: 0,
    vegan: 0,
    localized: 0,
    total_items: 0,
    enriched_items: 0,
  };
}

export function itemFlagLabels(item: MenuCompareItemDetail): string[] {
  const flags: string[] = [];
  if (!item.enriched) {
    flags.push("unenriched");
    return flags;
  }
  if (item.beverage_type === "alcoholic") flags.push("alcoholic");
  if (item.beverage_type === "non_alcoholic") flags.push("non-alcoholic");
  if (item.is_vegetarian) flags.push("vegetarian");
  if (item.is_vegan) flags.push("vegan");
  if (item.is_localized) flags.push("localised");
  return flags;
}
