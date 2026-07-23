import type { MenuCompareResponse } from "@/lib/api";
import { buildCsv } from "@/lib/csv";
import {
  formatMenuFlightLabel,
  MENU_ALL_CATEGORIES,
} from "@/lib/menu-fields";

const HEADERS = [
  "cabin_class",
  "item_type",
  "category",
  "subcategory",
  "flight",
  "menu_item",
  "menu_item_description",
  "is_alcoholic",
  "non_alcoholic",
  "vegan",
  "vegetarian",
  "localised",
  "localised_note",
  "vegetarian_confidence",
  "vegan_confidence",
  "confidence_level",
] as const;

function formatBool(value: boolean | null | undefined): string {
  if (value == null) return "";
  return value ? "true" : "false";
}

function formatConfidence(value: number | null | undefined): string {
  if (value == null) return "";
  return String(Math.round(value * 100));
}

export function buildMenuItemCsv(
  compare: MenuCompareResponse,
  categoryFilter: string = MENU_ALL_CATEGORIES
): string {
  const filteredRows =
    categoryFilter === MENU_ALL_CATEGORIES
      ? compare.detail_rows
      : compare.detail_rows.filter(
          (row) => (row.category || "Uncategorised") === categoryFilter
        );

  const rows: string[][] = [];

  for (const row of filteredRows) {
    const category = row.category || "Uncategorised";
    const subcategory = row.subcategory || "—";

    for (const col of compare.columns) {
      const items = row.values[col.observation_id] ?? [];
      const flight = formatMenuFlightLabel(col);

      for (const item of items) {
        rows.push([
          compare.cabin,
          item.item_type ?? "",
          category,
          subcategory,
          flight,
          item.title || item.code || "Untitled",
          item.desc ?? "",
          formatBool(
            item.beverage_type == null
              ? null
              : item.beverage_type === "alcoholic"
          ),
          formatBool(
            item.beverage_type == null
              ? null
              : item.beverage_type === "non_alcoholic"
          ),
          formatBool(item.is_vegan),
          formatBool(item.is_vegetarian),
          formatBool(item.is_localized),
          item.localization_note ?? "",
          formatConfidence(item.vegetarian_confidence),
          formatConfidence(item.vegan_confidence),
          formatConfidence(item.localization_confidence),
        ]);
      }
    }
  }

  return buildCsv([...HEADERS], rows);
}
