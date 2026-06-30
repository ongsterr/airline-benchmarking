"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AirlineBadge } from "@/components/airline-badge";
import { LoadingState, EmptyTableRow } from "@/components/loading-state";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { TableToolbar } from "@/components/table-toolbar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import { AircraftListItem, getAircraftList } from "@/lib/api";
import { cn } from "@/lib/utils";

const AIRLINES = [
  { slug: "all", name: "All airlines" },
  { slug: "ek", name: "Emirates" },
  { slug: "ba", name: "British Airways" },
  { slug: "ai", name: "Air India" },
];

export default function FleetPageClient() {
  const searchParams = useSearchParams();
  const [items, setItems] = useState<AircraftListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [airline, setAirline] = useState(searchParams.get("airline") || "all");
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAircraftList({
        airline: airline === "all" ? undefined : airline,
        search: search || undefined,
      });
      setItems(data.items);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [airline, search]);

  useEffect(() => {
    load();
  }, [load]);

  const toggleSelect = (svgId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(svgId)) next.delete(svgId);
      else if (next.size < 4) next.add(svgId);
      return next;
    });
  };

  const compareUrl = `/compare?ids=${Array.from(selected).join(",")}`;

  const filters = (
    <TableToolbar>
      <Select value={airline} onValueChange={(v) => v && setAirline(v)}>
        <SelectTrigger className={cn("h-8 text-xs", CONTROL_WIDTH.sm)}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {AIRLINES.map((a) => (
            <SelectItem key={a.slug} value={a.slug} className="text-xs">
              {a.name}
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
                      onCheckedChange={() => toggleSelect(item.svg_id)}
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

      {selected.size >= 2 && (
        <div className="sticky bottom-4 flex justify-end">
          <Card>
            <CardContent className="flex items-center gap-3 px-4 py-2">
              <span className="text-xs text-muted-foreground">
                {selected.size} selected
              </span>
              <Button size="sm" render={<Link href={compareUrl} />}>
                Compare
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
