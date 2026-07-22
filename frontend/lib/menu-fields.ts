import type {
  MenuCompareDetailRow,
  MenuCompareItemDetail,
  MenuCompareResponse,
  MenuItemType,
  MenuMetricCounts,
} from "@/lib/api";

export const MENU_ITEM_TYPE_OPTIONS = [
  { value: "all", label: "All items" },
  { value: "food", label: "Food" },
  { value: "beverage", label: "Beverage" },
] as const;

export const MENU_ALL_CATEGORIES = "all" as const;

export const MENU_SUMMARY_METRICS = [
  { key: "alcoholic", label: "Alcoholic" },
  { key: "non_alcoholic", label: "Non-alcoholic" },
  { key: "vegetarian", label: "Vegetarian" },
  { key: "vegan", label: "Vegan" },
  { key: "localized", label: "Localised" },
] as const;

export type MenuSummaryMetricKey = (typeof MENU_SUMMARY_METRICS)[number]["key"];

export type MenuFoodTypeKey = MenuItemType | "unenriched";

export type MenuPivotedRow = {
  foodType: MenuFoodTypeKey;
  foodTypeLabel: string;
  subcategory: string;
  values: Record<string, MenuCompareItemDetail[]>;
  summaryValues: Record<string, MenuMetricCounts>;
};

const FOOD_TYPE_ORDER: MenuFoodTypeKey[] = ["food", "beverage", "unenriched"];

const FOOD_TYPE_LABELS: Record<MenuFoodTypeKey, string> = {
  food: "Food",
  beverage: "Beverage",
  unenriched: "Unenriched",
};

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

export function metricCountsFromItems(
  items: MenuCompareItemDetail[]
): MenuMetricCounts {
  const counts = emptyMetricCounts();
  counts.total_items = items.length;
  for (const item of items) {
    if (item.enriched) counts.enriched_items += 1;
    if (item.beverage_type === "alcoholic") counts.alcoholic += 1;
    if (item.beverage_type === "non_alcoholic") counts.non_alcoholic += 1;
    if (item.is_vegetarian === true) counts.vegetarian += 1;
    if (item.is_vegan === true) counts.vegan += 1;
    if (item.is_localized === true) counts.localized += 1;
  }
  return counts;
}

function foodTypeKey(item: MenuCompareItemDetail): MenuFoodTypeKey {
  if (item.item_type === "food" || item.item_type === "beverage") {
    return item.item_type;
  }
  return "unenriched";
}

export function listMenuSourceCategories(
  detailRows: MenuCompareDetailRow[]
): string[] {
  const seen = new Set<string>();
  const categories: string[] = [];
  for (const row of detailRows) {
    const category = row.category || "Uncategorised";
    if (seen.has(category)) continue;
    seen.add(category);
    categories.push(category);
  }
  return categories;
}

export function pivotMenuCompareRows(
  compare: MenuCompareResponse,
  categoryFilter: string = MENU_ALL_CATEGORIES
): MenuPivotedRow[] {
  const observationIds = compare.columns.map((col) => col.observation_id);
  const filteredRows =
    categoryFilter === MENU_ALL_CATEGORIES
      ? compare.detail_rows
      : compare.detail_rows.filter(
          (row) => (row.category || "Uncategorised") === categoryFilter
        );

  // foodType -> subcategory -> observation_id -> items
  const grouped = new Map<
    MenuFoodTypeKey,
    Map<string, Record<string, MenuCompareItemDetail[]>>
  >();
  const subcategoryOrder = new Map<MenuFoodTypeKey, string[]>();

  for (const foodType of FOOD_TYPE_ORDER) {
    grouped.set(foodType, new Map());
    subcategoryOrder.set(foodType, []);
  }

  for (const row of filteredRows) {
    const subcategory = row.subcategory || "—";
    for (const observationId of observationIds) {
      const items = row.values[observationId] ?? [];
      for (const item of items) {
        const foodType = foodTypeKey(item);
        const bySub = grouped.get(foodType)!;
        if (!bySub.has(subcategory)) {
          bySub.set(subcategory, {});
          subcategoryOrder.get(foodType)!.push(subcategory);
        }
        const values = bySub.get(subcategory)!;
        if (!values[observationId]) values[observationId] = [];
        values[observationId].push(item);
      }
    }
  }

  const pivoted: MenuPivotedRow[] = [];
  for (const foodType of FOOD_TYPE_ORDER) {
    for (const subcategory of subcategoryOrder.get(foodType) ?? []) {
      const values = grouped.get(foodType)!.get(subcategory) ?? {};
      const summaryValues: Record<string, MenuMetricCounts> = {};
      for (const observationId of observationIds) {
        const items = values[observationId] ?? [];
        values[observationId] = items;
        summaryValues[observationId] = metricCountsFromItems(items);
      }
      pivoted.push({
        foodType,
        foodTypeLabel: FOOD_TYPE_LABELS[foodType],
        subcategory,
        values,
        summaryValues,
      });
    }
  }
  return pivoted;
}
