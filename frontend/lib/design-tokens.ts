/** Shared layout and table class contracts (Linear light + LCM density). */

export const CONTROL_WIDTH = {
  sm: "w-40",
  md: "w-44",
} as const;

export const TOOLBAR_CONTROL_CLASS =
  "h-8 text-[11px] md:text-[11px] *:data-[slot=select-value]:text-[11px] md:*:data-[slot=select-value]:text-[11px]";

export const TABLE_HEAD_CLASS =
  "h-8 text-xs font-medium text-muted-foreground";

export const TABLE_ROW_CLASS = "text-xs";

export const TABLE_CELL_CLASS = "py-2";

export const TABLE_CELL_NUMERIC_CLASS = "py-2 text-right tabular-nums";

export const TABLE_CELL_MUTED_CLASS = "py-2 text-muted-foreground";

export const TABLE_LINK_CLASS = "text-primary hover:underline";

export const COMPARE_EDIT_FIELD_CLASS =
  "h-7 w-full text-xs md:text-xs tabular-nums";

/** Fixed-width airline compare columns; requires `table-fixed` on the table. */
export const COMPARE_AIRLINE_COLUMN_CLASS =
  "w-48 max-w-48 min-w-32 align-top text-left !whitespace-normal break-words [overflow-wrap:anywhere]";

export const COMPARE_FEATURE_COLUMN_CLASS =
  "w-40 min-w-32 align-top text-left !whitespace-normal";

export const CABINS = [
  { key: "first", label: "First" },
  { key: "business", label: "Business" },
  { key: "premium_economy", label: "Premium Economy" },
  { key: "economy", label: "Economy" },
] as const;

export type CabinKey = (typeof CABINS)[number]["key"];

/** Linear-style issue label tints for airline badges. */
export const AIRLINE_LABEL_CLASSES: Record<string, string> = {
  ek: "bg-label-red/10 text-label-red border-label-red/25",
  ba: "bg-label-blue/10 text-label-blue border-label-blue/25",
  ai: "bg-label-orange/10 text-label-orange border-label-orange/25",
};

export function airlineLabelClass(slug: string): string {
  return AIRLINE_LABEL_CLASSES[slug] ?? "";
}
