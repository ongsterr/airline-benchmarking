"use client";

import { Fragment, useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Download } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { EmptyTableRow, LoadingState } from "@/components/loading-state";
import { MenuExtractSection } from "@/components/menu-extract-section";
import { MenuFlightSelector } from "@/components/menu-flight-selector";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { SignInDialog } from "@/components/sign-in-dialog";
import { TableToolbar } from "@/components/table-toolbar";
import { Button } from "@/components/ui/button";
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
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
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
import { downloadCsv } from "@/lib/csv";
import {
  emptyMetricCounts,
  formatMenuFlightLabel,
  itemFlagLabels,
  listMenuSourceCategories,
  MENU_ALL_CATEGORIES,
  MENU_ITEM_TYPE_OPTIONS,
  MENU_SUMMARY_METRICS,
  pivotMenuCompareRows,
  SUMMARY_METRICS_BY_FOOD_TYPE,
  type MenuFoodTypeKey,
} from "@/lib/menu-fields";
import { buildMenuItemCsv } from "@/lib/menu-item-csv";
import { useEditAuth } from "@/lib/use-edit-auth";
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
  foodType,
}: {
  counts: MenuMetricCounts;
  available: boolean;
  foodType: MenuFoodTypeKey;
}) {
  if (!available) {
    return (
      <p className="text-[11px] text-muted-foreground">Menu unavailable</p>
    );
  }
  if (counts.total_items === 0) {
    return <p className="text-[11px] text-muted-foreground">—</p>;
  }

  const metricKeys = SUMMARY_METRICS_BY_FOOD_TYPE[foodType];
  const metrics = MENU_SUMMARY_METRICS.filter((m) => metricKeys.includes(m.key));
  const unenrichedCount = counts.total_items - counts.enriched_items;

  if (metrics.length === 0) {
    return (
      <p className="text-[11px] text-muted-foreground">
        {unenrichedCount > 0
          ? `${unenrichedCount} unenriched`
          : `${counts.total_items} item${counts.total_items === 1 ? "" : "s"}`}
      </p>
    );
  }

  return (
    <ul className="space-y-0.5 text-[11px] tabular-nums">
      {metrics.map((metric) => {
        const isLocalized = metric.key === "localized";
        return (
          <li key={metric.key} className="flex justify-between gap-3">
            <span
              className={cn(
                isLocalized
                  ? "font-semibold text-primary"
                  : "text-muted-foreground"
              )}
            >
              {metric.label}
            </span>
            <span
              className={cn(
                "font-medium",
                isLocalized && "font-semibold text-primary"
              )}
            >
              {counts[metric.key]}
            </span>
          </li>
        );
      })}
      {unenrichedCount > 0 && (
        <li className="pt-0.5 text-muted-foreground">
          {unenrichedCount} unenriched
        </li>
      )}
    </ul>
  );
}

function EnrichmentFlag({
  label,
  confidence,
  note,
  emphasized = false,
}: {
  label: string;
  confidence: number | null | undefined;
  note?: string | null;
  emphasized?: boolean;
}) {
  const confidencePct =
    confidence != null ? Math.round(confidence * 100) : null;
  const triggerClass = emphasized
    ? "cursor-default font-semibold uppercase tracking-wide text-primary"
    : "cursor-default uppercase tracking-wide";
  return (
    <Tooltip>
      <TooltipTrigger className={triggerClass}>{label}</TooltipTrigger>
      <TooltipContent className="max-w-xs flex-col items-start gap-0.5 whitespace-normal text-left">
        {note && <p>{note}</p>}
        {confidencePct != null && <p>Confidence {confidencePct}%</p>}
      </TooltipContent>
    </Tooltip>
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
            <p className="font-medium leading-snug">
              {item.title || item.code || "Untitled"}
            </p>
            {item.desc && (
              <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                {item.desc}
              </p>
            )}
            {flags.length > 0 && (
              <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                {flags.map((flag, index) => (
                  <span key={flag} className="inline-flex items-center gap-1.5">
                    {index > 0 && <span aria-hidden>·</span>}
                    {flag === "localised" ? (
                      <EnrichmentFlag
                        label="localised"
                        confidence={item.localization_confidence}
                        note={item.localization_note}
                        emphasized
                      />
                    ) : flag === "vegetarian" ? (
                      <EnrichmentFlag
                        label="vegetarian"
                        confidence={item.vegetarian_confidence}
                      />
                    ) : flag === "vegan" ? (
                      <EnrichmentFlag
                        label="vegan"
                        confidence={item.vegan_confidence}
                      />
                    ) : (
                      <span>{flag}</span>
                    )}
                  </span>
                ))}
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
  const [category, setCategory] = useState<string>(() => {
    return searchParams.get("category") || MENU_ALL_CATEGORIES;
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

  const { isAuthenticated, isLoading: authLoading, login } = useEditAuth();
  const [signInOpen, setSignInOpen] = useState(false);
  const [signInPassword, setSignInPassword] = useState("");
  const [signInError, setSignInError] = useState<string | null>(null);
  const [signingIn, setSigningIn] = useState(false);
  const [exporting, setExporting] = useState(false);

  const canTrigger = isAuthenticated;

  const openSignIn = useCallback(() => {
    setSignInError(null);
    setSignInOpen(true);
  }, []);

  const handleSignIn = async (e: FormEvent) => {
    e.preventDefault();
    setSignInError(null);
    setSigningIn(true);
    try {
      await login(signInPassword);
      setSignInOpen(false);
      setSignInPassword("");
    } catch (err) {
      setSignInError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setSigningIn(false);
    }
  };

  const syncUrl = useCallback(
    (next: {
      cabin?: CabinKey;
      item_type?: MenuItemTypeFilter;
      category?: string;
      ids?: string[];
    }) => {
      const params = new URLSearchParams(searchParams.toString());
      const nextCabin = next.cabin ?? cabin;
      const nextType = next.item_type ?? itemType;
      const nextCategory = next.category ?? category;
      const nextIds = next.ids ?? selectedIds;
      params.set("cabin", nextCabin);
      params.set("item_type", nextType);
      if (nextCategory && nextCategory !== MENU_ALL_CATEGORIES) {
        params.set("category", nextCategory);
      } else {
        params.delete("category");
      }
      if (nextIds.length > 0) {
        params.set("ids", nextIds.join(","));
      } else {
        params.delete("ids");
      }
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [cabin, category, itemType, pathname, router, searchParams, selectedIds]
  );

  const refreshMenuData = useCallback(async () => {
    try {
      const data = await getMenuFilterOptions({ cabin, item_type: itemType });
      setOptions(data.observations);
      setOptionsError(null);
      const valid = new Set(data.observations.map((o) => o.observation_id));
      setSelectedIds((prev) => {
        const next = prev.filter((id) => valid.has(id));
        if (next.length !== prev.length) {
          syncUrl({ ids: next });
        }
        return next;
      });
    } catch {
      // Keep existing options on refresh failure.
    }

    if (selectedIds.length < MIN_COMPARE_CONFIGS) {
      return;
    }
    try {
      const data = await getMenuCompare(selectedIds, {
        cabin,
        item_type: itemType,
      });
      setCompare(data);
      setCompareError(null);
    } catch {
      // Keep existing compare on refresh failure.
    }
  }, [cabin, itemType, selectedIds, syncUrl]);

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

  const sourceCategories = useMemo(
    () => (compare ? listMenuSourceCategories(compare.detail_rows) : []),
    [compare]
  );

  // Clamp stale category when the loaded compare payload no longer includes it.
  if (
    compare &&
    sourceCategories.length > 0 &&
    category !== MENU_ALL_CATEGORIES &&
    !sourceCategories.includes(category)
  ) {
    setCategory(MENU_ALL_CATEGORIES);
  }

  const activeCategory =
    !compare ||
    category === MENU_ALL_CATEGORIES ||
    sourceCategories.includes(category)
      ? category
      : MENU_ALL_CATEGORIES;

  useEffect(() => {
    const urlCategory = searchParams.get("category");
    if (!urlCategory) return;
    if (!compare || sourceCategories.length === 0) return;
    if (sourceCategories.includes(urlCategory)) return;
    const params = new URLSearchParams(searchParams.toString());
    params.delete("category");
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }, [compare, pathname, router, searchParams, sourceCategories]);

  const pivotedRows = useMemo(
    () => (compare ? pivotMenuCompareRows(compare, activeCategory) : []),
    [compare, activeCategory]
  );

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
    setCategory(MENU_ALL_CATEGORIES);
    syncUrl({ cabin: value, ids: [], category: MENU_ALL_CATEGORIES });
  };

  const handleItemTypeChange = (value: string | null) => {
    if (!isItemTypeFilter(value)) return;
    setItemType(value);
    setSelectedIds([]);
    setCategory(MENU_ALL_CATEGORIES);
    syncUrl({ item_type: value, ids: [], category: MENU_ALL_CATEGORIES });
  };

  const handleCategoryChange = (value: string | null) => {
    const next = value || MENU_ALL_CATEGORIES;
    setCategory(next);
    syncUrl({ category: next });
  };

  const handleSelectionChange = (ids: string[]) => {
    const next = ids.slice(0, MAX_COMPARE_CONFIGS);
    setSelectedIds(next);
    syncUrl({ ids: next });
  };

  const handleDownloadMenuCsv = () => {
    if (!compare || compareLoading || exporting) return;
    setExporting(true);
    try {
      const content = buildMenuItemCsv(compare, activeCategory);
      const filename = `menu-items-${cabin}-${new Date().toISOString().slice(0, 10)}.csv`;
      downloadCsv(content, filename);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to download CSV";
      window.alert(message);
    } finally {
      setExporting(false);
    }
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

  let lastFoodType = "";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Food & beverage"
        title="Menu Items Analysis"
        description="Compare onboard menu composition across Emirates flights for a cabin and item type."
      />

      <SectionCard title="Extract menu">
        <MenuExtractSection
          canTrigger={canTrigger}
          isAuthLoading={authLoading}
          onSignInRequired={openSignIn}
          onComplete={() => void refreshMenuData()}
        />
      </SectionCard>

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

            <Select
              value={activeCategory}
              onValueChange={handleCategoryChange}
              disabled={!compare}
            >
              <SelectTrigger className={cn(TOOLBAR_CONTROL_CLASS, "w-48")}>
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={MENU_ALL_CATEGORIES}>All categories</SelectItem>
                {sourceCategories.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat}
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

            <Button
              size="sm"
              variant="outline"
              className="ml-auto"
              disabled={!compare || pivotedRows.length === 0 || exporting}
              onClick={handleDownloadMenuCsv}
            >
              <Download className="mr-1 h-3 w-3" />
              {exporting ? "Exporting..." : "Download CSV"}
            </Button>
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
                      Subcategory
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
                  ) : !compare || pivotedRows.length === 0 ? (
                    <EmptyTableRow
                      colSpan={colSpan}
                      message="No menu items for the selected flights."
                    />
                  ) : (
                    pivotedRows.map((row) => {
                      const showFoodType = row.foodType !== lastFoodType;
                      lastFoodType = row.foodType;
                      return (
                        <Fragment key={`${row.foodType}::${row.subcategory}`}>
                          {showFoodType && (
                            <TableRow className="bg-muted/40 hover:bg-muted/40">
                              <TableCell
                                colSpan={colSpan}
                                className="py-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
                              >
                                {row.foodTypeLabel}
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
                              {row.subcategory}
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
                                    row.summaryValues[col.observation_id] ??
                                    emptyMetricCounts()
                                  }
                                  available={col.available}
                                  foodType={row.foodType}
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
                      Subcategory
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
                  ) : !compare || pivotedRows.length === 0 ? (
                    <EmptyTableRow
                      colSpan={colSpan}
                      message="No menu items for the selected flights."
                    />
                  ) : (
                    (() => {
                      let detailFoodType = "";
                      return pivotedRows.map((row) => {
                        const showFoodType = row.foodType !== detailFoodType;
                        detailFoodType = row.foodType;
                        return (
                          <Fragment
                            key={`detail-${row.foodType}::${row.subcategory}`}
                          >
                            {showFoodType && (
                              <TableRow className="bg-muted/40 hover:bg-muted/40">
                                <TableCell
                                  colSpan={colSpan}
                                  className="py-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
                                >
                                  {row.foodTypeLabel}
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
                                {row.subcategory}
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

      <SignInDialog
        open={signInOpen}
        onOpenChange={setSignInOpen}
        password={signInPassword}
        onPasswordChange={setSignInPassword}
        error={signInError}
        signingIn={signingIn}
        onSubmit={handleSignIn}
        description="Enter the edit password to run menu extraction pipelines."
      />
    </div>
  );
}
