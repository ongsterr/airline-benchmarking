"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { X } from "lucide-react";
import { AirlineBadge } from "@/components/airline-badge";
import { LoadingState, EmptyTableRow } from "@/components/loading-state";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { TableToolbar } from "@/components/table-toolbar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
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
  CONTROL_WIDTH,
  TABLE_CELL_CLASS,
  TABLE_CELL_NUMERIC_CLASS,
  TABLE_HEAD_CLASS,
  TABLE_LINK_CLASS,
  TABLE_ROW_CLASS,
} from "@/lib/design-tokens";
import {
  AircraftListItem,
  AirlineSummary,
  getAircraftList,
  getAirlineSummaries,
} from "@/lib/api";
import { cn } from "@/lib/utils";

function parseIds(param: string | null): string[] {
  return param?.split(",").filter(Boolean) ?? [];
}

export default function FleetPageClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [summaries, setSummaries] = useState<AirlineSummary[]>([]);
  const [items, setItems] = useState<AircraftListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(parseIds(searchParams.get("ids")))
  );
  const [selectedMeta, setSelectedMeta] = useState<
    Map<string, AircraftListItem>
  >(new Map());
  const [airline, setAirline] = useState(searchParams.get("airline") || "all");
  const [aircraftType, setAircraftType] = useState("all");
  const [search, setSearch] = useState("");
  const idsParam = searchParams.get("ids") || "";

  const aircraftTypes = useMemo(() => {
    const types = new Set<string>();
    for (const s of summaries) {
      for (const t of s.aircraft_types) types.add(t);
    }
    return Array.from(types).sort();
  }, [summaries]);

  useEffect(() => {
    getAirlineSummaries()
      .then(setSummaries)
      .catch(() => setSummaries([]));
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

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAircraftList({
        airline: airline === "all" ? undefined : airline,
        aircraft_type: aircraftType === "all" ? undefined : aircraftType,
        search: search || undefined,
      });
      setItems(data.items);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [airline, aircraftType, search]);

  useEffect(() => {
    load();
  }, [load]);

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

    getAircraftList()
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
    } else if (selected.size < 4) {
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

  const filters = (
    <TableToolbar>
      <Select value={airline} onValueChange={(v) => v && setAirline(v)}>
        <SelectTrigger className={cn("h-8 text-xs", CONTROL_WIDTH.sm)}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all" className="text-xs">
            All airlines
          </SelectItem>
          {summaries.map((a) => (
            <SelectItem key={a.slug} value={a.slug} className="text-xs">
              {a.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select
        value={aircraftType}
        onValueChange={(v) => v && setAircraftType(v)}
      >
        <SelectTrigger className={cn("h-8 text-xs", CONTROL_WIDTH.sm)}>
          <SelectValue placeholder="Aircraft type" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all" className="text-xs">
            All types
          </SelectItem>
          {aircraftTypes.map((t) => (
            <SelectItem key={t} value={t} className="text-xs">
              {t}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Input
        placeholder="Search config..."
        className={cn("h-8 text-xs", CONTROL_WIDTH.sm)}
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
        description="Browse aircraft configurations and select up to four for comparison."
        actions={filters}
      />

      {airline !== "all" && (
        <p className="text-xs text-muted-foreground">
          Select &ldquo;All airlines&rdquo; to compare configurations across
          carriers.
        </p>
      )}

      {selected.size > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/30 px-3 py-2">
          <span className="text-xs text-muted-foreground">
            {selected.size} of 4 selected
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
          <div className="ml-auto">
            <Button
              size="sm"
              disabled={selected.size < 2}
              render={<Link href={compareUrl} />}
            >
              Compare
            </Button>
          </div>
        </div>
      )}

      <SectionCard title="Configurations">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className={cn(TABLE_HEAD_CLASS, "w-8")} />
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
              items.map((item) => (
                <TableRow key={item.svg_id} className={TABLE_ROW_CLASS}>
                  <TableCell className={TABLE_CELL_CLASS}>
                    <Checkbox
                      checked={selected.has(item.svg_id)}
                      onCheckedChange={() => toggleSelect(item)}
                      disabled={
                        !selected.has(item.svg_id) && selected.size >= 4
                      }
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
                      <span className="font-mono">{item.svg_id}</span>
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
              ))
            )}
          </TableBody>
        </Table>
      </SectionCard>
    </div>
  );
}
