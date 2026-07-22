"use client";

import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { EmptyState } from "@/components/empty-state";
import { EmptyTableRow, LoadingState } from "@/components/loading-state";
import { MenuFlightSelector } from "@/components/menu-flight-selector";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { TableToolbar } from "@/components/table-toolbar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  CABINS,
  COMPARE_AIRLINE_COLUMN_CLASS,
  COMPARE_FEATURE_COLUMN_CLASS,
  COMPARE_TABLE_HEAD_STICKY_CLASS,
  TABLE_HEAD_CLASS,
  TABLE_ROW_CLASS,
  TOOLBAR_CONTROL_CLASS,
  type CabinKey,
} from "@/lib/design-tokens";
import {
  getMenuCompare,
  getMenuFilterOptions,
  type MenuCompareResponse,
  type MenuFlightOption,
  type MenuItemTypeFilter,
  type MenuMetricCounts,
} from "@/lib/api";
import {
  MAX_COMPARE_CONFIGS,
  MIN_COMPARE_CONFIGS,
} from "@/lib/constants";
import {
  emptyMetricCounts,
  formatMenuFlightLabel,
  itemFlagLabels,
  MENU_ITEM_TYPE_OPTIONS,
  MENU_SUMMARY_METRICS,
} from "@/lib/menu-fields";
import { cn } from "@/lib/utils";

function parseIds(param: string | null): string[] {
  return param?.split(",").filter(Boolean) ?? [];
}

function isCabinKey(value: string | null): value is CabinKey {
  return CABINS.some((cabin) => cabin.key === value);
}

function isItemTypeFilter(value: string | null): value is MenuItemTypeFilter {
  return value === "all" || value === "food" || value === "beverage";
}

function SummaryCell({
  counts,
  available,
}: {
  counts: MenuMetricCounts;
  available: boolean;
}) {
  if (!available) {
    return (
      <p className="text-[11px] text-muted-foreground">Menu unavailable</p>
    );
  }
  if (counts.total_items === 0) {
    return <p className="text-[11px] text-muted-foreground">—</p>;
  }
  return (
    <ul className="space-y-0.5 text-[11px] tabular-nums">
      {MENU_SUMMARY_METRICS.map((metric) => (
        <li key={metric.key} className="flex justify-between gap-3">
          <span className="text-muted-foreground">{metric.label}</span>
          <span className="font-medium">{counts[metric.key]}</span>
        </li>
      ))}
      {counts.enriched_items < counts.total_items && (
        <li className="pt-0.5 text-muted-foreground">
          {counts.total_items - counts.enriched_items} unenriched
        </li>
      )}
    </ul>
  );
}

function DetailCell({
  items,
  available,
}: {
  items: MenuCompareResponse["detail_rows"][number]["values"][string];
  available: boolean;
}) {
  if (!available) {
    return (
      <p className="text-[11px] text-muted-foreground">Menu unavailable</p>
    );
  }
  if (!items || items.length === 0) {
    return <p className="text-[11px] text-muted-foreground">—</p>;
  }
  return (
    <ul className="space-y-2">
      {items.map((item) => {
        const flags = itemFlagLabels(item);
        return (
          <li key={item.item_hash || `${item.code}-${item.position}`}>
            <p className="font-medium leading-snug">{item.title || item.code || "Untitled"}</p>
            {item.desc && (
              <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                {item.desc}
              </p>
            )}
            {flags.length > 0 && (
              <p className="mt-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                {flags.join(" · ")}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

export default function MenuPageClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [cabin, setCabin] = useState<CabinKey>(() => {
    const param = searchParams.get("cabin");
    return isCabinKey(param) ? param : "business";
  });
  const [itemType, setItemType] = useState<MenuItemTypeFilter>(() => {
    const param = searchParams.get("item_type");
    return isItemTypeFilter(param) ? param : "all";
  });
  const [selectedIds, setSelectedIds] = useState<string[]>(() =>
    parseIds(searchParams.get("ids")).slice(0, MAX_COMPARE_CONFIGS)
  );

  const [options, setOptions] = useState<MenuFlightOption[]>([]);
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [optionsError, setOptionsError] = useState<string | null>(null);

  const [compare, setCompare] = useState<MenuCompareResponse | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);

  const syncUrl = useCallback(
    (next: {
      cabin?: CabinKey;
      item_type?: MenuItemTypeFilter;
      ids?: string[];
    }) => {
      const params = new URLSearchParams(searchParams.toString());
      const nextCabin = next.cabin ?? cabin;
      const nextType = next.item_type ?? itemType;
      const nextIds = next.ids ?? selectedIds;
      params.set("cabin", nextCabin);
      params.set("item_type", nextType);
      if (nextIds.length > 0) {
        params.set("ids", nextIds.join(","));
      } else {
        params.delete("ids");
      }
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [cabin, itemType, pathname, router, searchParams, selectedIds]
  );

  useEffect(() => {
    let cancelled = false;
    setOptionsLoading(true);
    setOptionsError(null);
    getMenuFilterOptions({ cabin, item_type: itemType })
      .then((data) => {
        if (cancelled) return;
        setOptions(data.observations);
        const valid = new Set(data.observations.map((o) => o.observation_id));
        setSelectedIds((prev) => {
          const next = prev.filter((id) => valid.has(id));
          if (next.length !== prev.length) {
            syncUrl({ ids: next });
          }
          return next;
        });
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setOptions([]);
        setOptionsError(err.message || "Failed to load flights");
      })
      .finally(() => {
        if (!cancelled) setOptionsLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // syncUrl intentionally omitted — only re-fetch when cabin/itemType change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cabin, itemType]);

  useEffect(() => {
    if (selectedIds.length < MIN_COMPARE_CONFIGS) {
      setCompare(null);
      setCompareError(null);
      setCompareLoading(false);
      return;
    }
    let cancelled = false;
    setCompareLoading(true);
    setCompareError(null);
    getMenuCompare(selectedIds, { cabin, item_type: itemType })
      .then((data) => {
        if (cancelled) return;
        setCompare(data);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setCompare(null);
        setCompareError(err.message || "Failed to load comparison");
      })
      .finally(() => {
        if (!cancelled) setCompareLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedIds, cabin, itemType]);

  const optionById = useMemo(() => {
    const map = new Map<string, MenuFlightOption>();
    for (const option of options) {
      map.set(option.observation_id, option);
    }
    return map;
  }, [options]);

  const handleCabinChange = (value: string | null) => {
    if (!isCabinKey(value)) return;
    setCabin(value);
    setSelectedIds([]);
    syncUrl({ cabin: value, ids: [] });
  };

  const handleItemTypeChange = (value: string | null) => {
    if (!isItemTypeFilter(value)) return;
    setItemType(value);
    setSelectedIds([]);
    syncUrl({ item_type: value, ids: [] });
  };

  const handleSelectionChange = (ids: string[]) => {
    const next = ids.slice(0, MAX_COMPARE_CONFIGS);
    setSelectedIds(next);
    syncUrl({ ids: next });
  };

  const columns = compare?.columns ?? [];
  const canCompare = selectedIds.length >= MIN_COMPARE_CONFIGS;
  const colSpan = Math.max(columns.length, 1) + 1;
  const headerColumns =
    columns.length > 0
      ? columns.map((col) => ({
          observation_id: col.observation_id,
          label: formatMenuFlightLabel(col),
          available: col.available,
        }))
      : selectedIds.map((id) => {
          const option = optionById.get(id);
          return {
            observation_id: id,
            label: option ? formatMenuFlightLabel(option) : id,
            available: option?.available ?? true,
          };
        });

  let lastCategory = "";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Food & beverage"
        title="Menu Items Analysis"
        description="Compare onboard menu composition across Emirates flights for a cabin and item type."
      />

      <SectionCard title="Filters" overflowVisible>
        <div className="px-4 py-3">
          <TableToolbar>
            <Select value={cabin} onValueChange={handleCabinChange}>
              <SelectTrigger className={cn(TOOLBAR_CONTROL_CLASS, "w-44")}>
                <SelectValue placeholder="Cabin" />
              </SelectTrigger>
              <SelectContent>
                {CABINS.map((c) => (
                  <SelectItem key={c.key} value={c.key}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={itemType} onValueChange={handleItemTypeChange}>
              <SelectTrigger className={cn(TOOLBAR_CONTROL_CLASS, "w-40")}>
                <SelectValue placeholder="Item type" />
              </SelectTrigger>
              <SelectContent>
                {MENU_ITEM_TYPE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <MenuFlightSelector
              options={options}
              selected={selectedIds}
              onChange={handleSelectionChange}
              disabled={optionsLoading}
            />

            <span className="text-[11px] text-muted-foreground">
              {optionsLoading
                ? "Loading flights…"
                : `${selectedIds.length} / ${MAX_COMPARE_CONFIGS} selected`}
            </span>
          </TableToolbar>
          {optionsError && (
            <p className="mt-2 text-xs text-destructive">{optionsError}</p>
          )}
        </div>
      </SectionCard>

      {!canCompare ? (
        <EmptyState
          message={`Select at least ${MIN_COMPARE_CONFIGS} flight / date combinations to compare.`}
        />
      ) : compareError ? (
        <EmptyState message={compareError} />
      ) : (
        <>
          <SectionCard title="Summary">
            <div className="overflow-x-auto">
              <Table className="table-fixed min-w-full">
                <TableHeader>
                  <TableRow>
                    <TableHead
                      className={cn(
                        TABLE_HEAD_CLASS,
                        COMPARE_FEATURE_COLUMN_CLASS,
                        COMPARE_TABLE_HEAD_STICKY_CLASS
                      )}
                    >
                      Category
                    </TableHead>
                    {headerColumns.map((col) => (
                      <TableHead
                        key={col.observation_id}
                        className={cn(
                          TABLE_HEAD_CLASS,
                          COMPARE_AIRLINE_COLUMN_CLASS,
                          COMPARE_TABLE_HEAD_STICKY_CLASS
                        )}
                      >
                        <div className="space-y-0.5">
                          <p className="font-medium text-foreground">{col.label}</p>
                          {!col.available && (
                            <p className="text-[10px] font-normal text-muted-foreground">
                              Unavailable
                            </p>
                          )}
                        </div>
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {compareLoading && !compare ? (
                    <LoadingState colSpan={colSpan} message="Loading summary…" />
                  ) : !compare || compare.summary_rows.length === 0 ? (
                    <EmptyTableRow
                      colSpan={colSpan}
                      message="No menu categories for the selected flights."
                    />
                  ) : (
                    compare.summary_rows.map((row) => {
                      const showCategory = row.category !== lastCategory;
                      lastCategory = row.category;
                      return (
                        <Fragment key={`${row.category}::${row.subcategory}`}>
                          {showCategory && (
                            <TableRow className="bg-muted/40 hover:bg-muted/40">
                              <TableCell
                                colSpan={colSpan}
                                className="py-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
                              >
                                {row.category || "Uncategorised"}
                              </TableCell>
                            </TableRow>
                          )}
                          <TableRow className={TABLE_ROW_CLASS}>
                            <TableCell
                              className={cn(
                                COMPARE_FEATURE_COLUMN_CLASS,
                                "align-top font-medium"
                              )}
                            >
                              {row.subcategory || "—"}
                            </TableCell>
                            {columns.map((col) => (
                              <TableCell
                                key={col.observation_id}
                                className={cn(
                                  COMPARE_AIRLINE_COLUMN_CLASS,
                                  "align-top"
                                )}
                              >
                                <SummaryCell
                                  counts={
                                    row.values[col.observation_id] ??
                                    emptyMetricCounts()
                                  }
                                  available={col.available}
                                />
                              </TableCell>
                            ))}
                          </TableRow>
                        </Fragment>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </div>
          </SectionCard>

          <SectionCard title="Item detail">
            <div className="overflow-x-auto">
              <Table className="table-fixed min-w-full">
                <TableHeader>
                  <TableRow>
                    <TableHead
                      className={cn(
                        TABLE_HEAD_CLASS,
                        COMPARE_FEATURE_COLUMN_CLASS,
                        COMPARE_TABLE_HEAD_STICKY_CLASS
                      )}
                    >
                      Category
                    </TableHead>
                    {columns.map((col) => (
                      <TableHead
                        key={col.observation_id}
                        className={cn(
                          TABLE_HEAD_CLASS,
                          COMPARE_AIRLINE_COLUMN_CLASS,
                          COMPARE_TABLE_HEAD_STICKY_CLASS
                        )}
                      >
                        {formatMenuFlightLabel(col)}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {compareLoading && !compare ? (
                    <LoadingState colSpan={colSpan} message="Loading details…" />
                  ) : !compare || compare.detail_rows.length === 0 ? (
                    <EmptyTableRow
                      colSpan={colSpan}
                      message="No menu items for the selected flights."
                    />
                  ) : (
                    (() => {
                      let detailCategory = "";
                      return compare.detail_rows.map((row) => {
                        const showCategory = row.category !== detailCategory;
                        detailCategory = row.category;
                        return (
                          <Fragment
                            key={`detail-${row.category}::${row.subcategory}`}
                          >
                            {showCategory && (
                              <TableRow className="bg-muted/40 hover:bg-muted/40">
                                <TableCell
                                  colSpan={colSpan}
                                  className="py-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
                                >
                                  {row.category || "Uncategorised"}
                                </TableCell>
                              </TableRow>
                            )}
                            <TableRow className={TABLE_ROW_CLASS}>
                              <TableCell
                                className={cn(
                                  COMPARE_FEATURE_COLUMN_CLASS,
                                  "align-top font-medium"
                                )}
                              >
                                {row.subcategory || "—"}
                              </TableCell>
                              {columns.map((col) => (
                                <TableCell
                                  key={col.observation_id}
                                  className={cn(
                                    COMPARE_AIRLINE_COLUMN_CLASS,
                                    "align-top"
                                  )}
                                >
                                  <DetailCell
                                    items={row.values[col.observation_id] ?? []}
                                    available={col.available}
                                  />
                                </TableCell>
                              ))}
                            </TableRow>
                          </Fragment>
                        );
                      });
                    })()
                  )}
                </TableBody>
              </Table>
            </div>
          </SectionCard>
        </>
      )}
    </div>
  );
}
