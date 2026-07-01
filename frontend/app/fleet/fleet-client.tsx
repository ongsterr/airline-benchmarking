"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Download, Loader2, X } from "lucide-react";
import { AirlineBadge } from "@/components/airline-badge";
import { LoadingState, EmptyTableRow } from "@/components/loading-state";
import { MultiSelectFilter } from "@/components/multi-select-filter";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { TableToolbar } from "@/components/table-toolbar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  CONTROL_WIDTH,
  TABLE_CELL_CLASS,
  TABLE_CELL_NUMERIC_CLASS,
  TABLE_HEAD_CLASS,
  TABLE_LINK_CLASS,
  TABLE_ROW_CLASS,
  TOOLBAR_CONTROL_CLASS,
} from "@/lib/design-tokens";
import {
  AircraftFilterOptions,
  AircraftListItem,
  AirlineSummary,
  downloadFleetCsv,
  getAircraftFilterOptions,
  getAircraftList,
  getAirlineSummaries,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  FLEET_LOOKUP_LIMIT,
  FLEET_PAGE_SIZE,
  MAX_COMPARE_CONFIGS,
  MIN_COMPARE_CONFIGS,
} from "@/lib/constants";

function parseIds(param: string | null): string[] {
  return param?.split(",").filter(Boolean) ?? [];
}

export default function FleetPageClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [summaries, setSummaries] = useState<AirlineSummary[]>([]);
  const [items, setItems] = useState<AircraftListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const loadMoreSentinelRef = useRef<HTMLTableRowElement>(null);
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(parseIds(searchParams.get("ids")))
  );
  const [selectedMeta, setSelectedMeta] = useState<
    Map<string, AircraftListItem>
  >(new Map());
  const [selectedAirlines, setSelectedAirlines] = useState<string[]>(() => {
    const param = searchParams.get("airline");
    if (!param || param === "all") return [];
    return parseIds(param);
  });
  const [selectedAircraftTypes, setSelectedAircraftTypes] = useState<string[]>(
    []
  );
  const [selectedHaulTypes, setSelectedHaulTypes] = useState<string[]>([]);
  const [selectedManufacturers, setSelectedManufacturers] = useState<string[]>(
    []
  );
  const [filterOptions, setFilterOptions] = useState<AircraftFilterOptions>({
    haul_types: [],
    manufacturers: [],
  });
  const [search, setSearch] = useState("");
  const [premiumEconomyOnly, setPremiumEconomyOnly] = useState(false);
  const [exporting, setExporting] = useState(false);
  const idsParam = searchParams.get("ids") || "";

  const aircraftTypes = useMemo(() => {
    const types = new Set<string>();
    for (const s of summaries) {
      for (const t of s.aircraft_types) types.add(t);
    }
    return Array.from(types).sort();
  }, [summaries]);

  const airlineOptions = useMemo(
    () => summaries.map((a) => ({ value: a.slug, label: a.name })),
    [summaries]
  );

  const aircraftTypeOptions = useMemo(
    () => aircraftTypes.map((t) => ({ value: t, label: t })),
    [aircraftTypes]
  );

  const haulTypeOptions = useMemo(
    () =>
      filterOptions.haul_types.map((haulType) => ({
        value: haulType,
        label: haulType,
      })),
    [filterOptions.haul_types]
  );

  const manufacturerOptions = useMemo(
    () =>
      filterOptions.manufacturers.map((manufacturer) => ({
        value: manufacturer,
        label: manufacturer,
      })),
    [filterOptions.manufacturers]
  );

  useEffect(() => {
    getAirlineSummaries()
      .then(setSummaries)
      .catch(() => setSummaries([]));
    getAircraftFilterOptions()
      .then(setFilterOptions)
      .catch(() => setFilterOptions({ haul_types: [], manufacturers: [] }));
  }, []);

  useEffect(() => {
    const ids = parseIds(searchParams.get("ids"));
    setSelected(new Set(ids));
  }, [searchParams]);

  const syncUrl = useCallback(
    (nextSelected: Set<string>) => {
      const params = new URLSearchParams(searchParams.toString());
      if (nextSelected.size > 0) {
        params.set("ids", Array.from(nextSelected).join(","));
      } else {
        params.delete("ids");
      }
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const listFilters = useMemo(
    () => ({
      airline: selectedAirlines.length > 0 ? selectedAirlines : undefined,
      aircraft_type:
        selectedAircraftTypes.length > 0 ? selectedAircraftTypes : undefined,
      haul_type: selectedHaulTypes.length > 0 ? selectedHaulTypes : undefined,
      manufacturer:
        selectedManufacturers.length > 0 ? selectedManufacturers : undefined,
      search: search || undefined,
      has_premium_economy: premiumEconomyOnly || undefined,
    }),
    [
      selectedAirlines,
      selectedAircraftTypes,
      selectedHaulTypes,
      selectedManufacturers,
      search,
      premiumEconomyOnly,
    ]
  );

  const hasMore = items.length < total;

  const fetchPage = useCallback(
    async (offset: number) => {
      return getAircraftList({
        ...listFilters,
        offset,
        limit: FLEET_PAGE_SIZE,
      });
    },
    [listFilters]
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setItems([]);
    setTotal(0);

    fetchPage(0)
      .then((data) => {
        if (cancelled) return;
        setItems(data.items);
        setTotal(data.total);
      })
      .catch(() => {
        if (cancelled) return;
        setItems([]);
        setTotal(0);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [fetchPage]);

  const loadMore = useCallback(async () => {
    if (loading || loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const data = await fetchPage(items.length);
      setTotal(data.total);
      setItems((prev) => {
        const seen = new Set(prev.map((item) => item.svg_id));
        const appended = data.items.filter((item) => !seen.has(item.svg_id));
        return [...prev, ...appended];
      });
    } catch {
      // Keep existing items on load-more failure.
    } finally {
      setLoadingMore(false);
    }
  }, [fetchPage, hasMore, items.length, loading, loadingMore]);

  useEffect(() => {
    const sentinel = loadMoreSentinelRef.current;
    if (!sentinel || loading || !hasMore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          void loadMore();
        }
      },
      { rootMargin: "200px" }
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMore, loadMore, loading, items.length]);

  useEffect(() => {
    setSelectedMeta((prev) => {
      const next = new Map(prev);
      for (const item of items) {
        if (selected.has(item.svg_id)) {
          next.set(item.svg_id, item);
        }
      }
      return next;
    });
  }, [items, selected]);

  useEffect(() => {
    const ids = parseIds(idsParam);
    if (ids.length === 0) return;

    getAircraftList({ limit: FLEET_LOOKUP_LIMIT })
      .then((data) => {
        setSelectedMeta((prev) => {
          const next = new Map(prev);
          for (const id of ids) {
            const item = data.items.find((i) => i.svg_id === id);
            if (item) next.set(id, item);
          }
          return next;
        });
      })
      .catch(() => {});
  }, [idsParam]);

  const updateSelection = (next: Set<string>) => {
    setSelected(next);
    syncUrl(next);
  };

  const toggleSelect = (item: AircraftListItem) => {
    const svgId = item.svg_id;
    if (selected.has(svgId)) {
      const next = new Set(selected);
      next.delete(svgId);
      setSelectedMeta((prev) => {
        const meta = new Map(prev);
        meta.delete(svgId);
        return meta;
      });
      updateSelection(next);
    } else {
      const next = new Set(selected);
      next.add(svgId);
      setSelectedMeta((prev) => new Map(prev).set(svgId, item));
      updateSelection(next);
    }
  };

  const removeSelected = (svgId: string) => {
    const next = new Set(selected);
    next.delete(svgId);
    setSelectedMeta((prev) => {
      const meta = new Map(prev);
      meta.delete(svgId);
      return meta;
    });
    updateSelection(next);
  };

  const compareUrl = `/compare?ids=${Array.from(selected).join(",")}`;
  const visibleIds = useMemo(() => items.map((item) => item.svg_id), [items]);
  const allVisibleSelected =
    visibleIds.length > 0 && visibleIds.every((svgId) => selected.has(svgId));
  const someVisibleSelected =
    visibleIds.some((svgId) => selected.has(svgId)) && !allVisibleSelected;

  const toggleSelectAllVisible = (checked: boolean) => {
    const next = new Set(selected);
    if (checked) {
      for (const item of items) {
        next.add(item.svg_id);
      }
      setSelectedMeta((prev) => {
        const meta = new Map(prev);
        for (const item of items) {
          if (next.has(item.svg_id)) meta.set(item.svg_id, item);
        }
        return meta;
      });
    } else {
      for (const item of items) next.delete(item.svg_id);
      setSelectedMeta((prev) => {
        const meta = new Map(prev);
        for (const item of items) meta.delete(item.svg_id);
        return meta;
      });
    }
    updateSelection(next);
  };

  const handleSelectAllVisible = () => {
    const shouldSelect = !allVisibleSelected && !someVisibleSelected;
    toggleSelectAllVisible(shouldSelect);
  };

  const handleDownloadCsv = async () => {
    if (selected.size === 0 || exporting) return;
    setExporting(true);
    try {
      await downloadFleetCsv(Array.from(selected));
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to download CSV";
      window.alert(message);
    } finally {
      setExporting(false);
    }
  };

  const filters = (
    <TableToolbar>
      <MultiSelectFilter
        emptyLabel="All airlines"
        options={airlineOptions}
        selected={selectedAirlines}
        onChange={setSelectedAirlines}
      />
      <MultiSelectFilter
        emptyLabel="All types"
        options={aircraftTypeOptions}
        selected={selectedAircraftTypes}
        onChange={setSelectedAircraftTypes}
      />
      <MultiSelectFilter
        emptyLabel="All haul types"
        options={haulTypeOptions}
        selected={selectedHaulTypes}
        onChange={setSelectedHaulTypes}
      />
      <MultiSelectFilter
        emptyLabel="All manufacturers"
        options={manufacturerOptions}
        selected={selectedManufacturers}
        onChange={setSelectedManufacturers}
      />
      <label className="flex h-8 items-center gap-1.5 px-1 text-[11px] text-muted-foreground">
        <Checkbox
          checked={premiumEconomyOnly}
          onCheckedChange={(checked) => setPremiumEconomyOnly(Boolean(checked))}
        />
        Premium economy
      </label>
      <Input
        placeholder="Search config..."
        className={cn(TOOLBAR_CONTROL_CLASS, CONTROL_WIDTH.sm)}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
    </TableToolbar>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Fleet explorer"
        title="Fleet configurations"
        description="Browse aircraft configurations, export any number of selected rows as CSV, and compare up to eight at once."
        actions={filters}
      />

      {selectedAirlines.length === 1 && (
        <p className="text-xs text-muted-foreground">
          Select multiple airlines (or clear the filter) to compare configurations
          across carriers.
        </p>
      )}

      {selected.size > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/30 px-3 py-2">
          <span className="text-xs text-muted-foreground">
            {selected.size} selected
          </span>
          {Array.from(selected).map((svgId) => {
            const meta = selectedMeta.get(svgId);
            return (
              <Badge
                key={svgId}
                variant="secondary"
                className="flex items-center gap-1.5 pr-1 font-normal"
              >
                {meta ? (
                  <>
                    <AirlineBadge
                      slug={meta.airline_slug}
                      name={meta.airline_name}
                    />
                    <span className="text-muted-foreground">·</span>
                    <span>{meta.aircraft_type_displayed || svgId}</span>
                    {meta.aircraft_code_displayed && (
                      <>
                        <span className="text-muted-foreground">·</span>
                        <span className="font-mono">
                          {meta.aircraft_code_displayed}
                        </span>
                      </>
                    )}
                  </>
                ) : (
                  <span className="font-mono">{svgId}</span>
                )}
                <button
                  type="button"
                  onClick={() => removeSelected(svgId)}
                  className="ml-0.5 rounded p-0.5 hover:bg-muted"
                  aria-label={`Remove ${svgId}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            );
          })}
          <div className="ml-auto flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={exporting}
              onClick={handleDownloadCsv}
            >
              <Download className="mr-1 h-3 w-3" />
              {exporting ? "Exporting..." : "Download CSV"}
            </Button>
            <Button
              size="sm"
              disabled={
                selected.size < MIN_COMPARE_CONFIGS ||
                selected.size > MAX_COMPARE_CONFIGS
              }
              nativeButton={false}
              render={<Link href={compareUrl} />}
            >
              Compare
            </Button>
          </div>
        </div>
      )}
      {selected.size > MAX_COMPARE_CONFIGS && (
        <p className="text-xs text-muted-foreground">
          Compare supports up to {MAX_COMPARE_CONFIGS} configs; refine your
          selection to compare.
        </p>
      )}

      <SectionCard title="Configurations">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className={cn(TABLE_HEAD_CLASS, "w-8")}>
                <Checkbox
                  aria-label="Select all visible configurations"
                  checked={allVisibleSelected}
                  indeterminate={someVisibleSelected}
                  onCheckedChange={handleSelectAllVisible}
                  disabled={loading || items.length === 0}
                />
              </TableHead>
              <TableHead className={TABLE_HEAD_CLASS}>Airline</TableHead>
              <TableHead className={TABLE_HEAD_CLASS}>Aircraft type</TableHead>
              <TableHead className={TABLE_HEAD_CLASS}>Config ID</TableHead>
              <TableHead className={TABLE_HEAD_CLASS}>Seat layout</TableHead>
              <TableHead className={cn(TABLE_HEAD_CLASS, "text-right")}>
                Seats
              </TableHead>
              <TableHead className={TABLE_HEAD_CLASS}>Ref URL</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <LoadingState colSpan={7} />
            ) : items.length === 0 ? (
              <EmptyTableRow
                colSpan={7}
                message="No configurations found."
              />
            ) : (
              <>
                {items.map((item) => (
                  <TableRow key={item.svg_id} className={TABLE_ROW_CLASS}>
                    <TableCell className={TABLE_CELL_CLASS}>
                      <Checkbox
                        checked={selected.has(item.svg_id)}
                        onCheckedChange={() => toggleSelect(item)}
                      />
                    </TableCell>
                    <TableCell className={TABLE_CELL_CLASS}>
                      <AirlineBadge
                        slug={item.airline_slug}
                        name={item.airline_name}
                      />
                    </TableCell>
                    <TableCell className={TABLE_CELL_CLASS}>
                      {item.aircraft_type_displayed || "—"}
                    </TableCell>
                    <TableCell className={TABLE_CELL_CLASS}>
                      <div className="flex items-center gap-1.5">
                        <Link
                          href={`/aircraft/${item.svg_id}`}
                          className={cn("font-mono", TABLE_LINK_CLASS)}
                        >
                          {item.svg_id}
                        </Link>
                        {item.is_dual_deck && (
                          <Badge
                            variant="secondary"
                            className="h-4 px-1 text-[10px] font-normal"
                          >
                            Dual deck
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className={TABLE_CELL_CLASS}>
                      {item.configuration || "—"}
                    </TableCell>
                    <TableCell className={TABLE_CELL_NUMERIC_CLASS}>
                      {item.total_seats ?? "—"}
                    </TableCell>
                    <TableCell className={TABLE_CELL_CLASS}>
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={cn("font-mono", TABLE_LINK_CLASS)}
                      >
                        {item.svg_id}
                      </a>
                    </TableCell>
                  </TableRow>
                ))}
                {hasMore && (
                  <TableRow ref={loadMoreSentinelRef} className="hover:bg-transparent">
                    <TableCell colSpan={7} className="py-3 text-center">
                      {loadingMore ? (
                        <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                          <Loader2 className="size-3.5 animate-spin" />
                          Loading more…
                        </span>
                      ) : (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="text-xs"
                          onClick={() => void loadMore()}
                        >
                          Load more
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                )}
              </>
            )}
          </TableBody>
        </Table>
        {!loading && total > 0 && (
          <div className="border-t px-4 py-2 text-xs text-muted-foreground">
            Showing {items.length} of {total} configurations
          </div>
        )}
      </SectionCard>
    </div>
  );
}
