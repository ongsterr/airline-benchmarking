"use client";

import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { Fragment, useEffect, useState } from "react";
import { AirlineBadge } from "@/components/airline-badge";
import { LoadingState } from "@/components/loading-state";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  CABINS,
  COMPARE_AIRLINE_COLUMN_CLASS,
  COMPARE_FEATURE_COLUMN_CLASS,
  TABLE_HEAD_CLASS,
  TABLE_LINK_CLASS,
  TABLE_ROW_CLASS,
  type CabinKey,
} from "@/lib/design-tokens";
import { CABIN_FIELDS, formatCompareValue } from "@/lib/compare-fields";
import { FLIGHT_FIELDS, flightFieldLabel, formatFlightValue } from "@/lib/flight-fields";
import { AircraftDetail, getAircraftDetail } from "@/lib/api";
import { cn } from "@/lib/utils";

function hardwareFieldLabel(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function AircraftDetailClient({ svgId }: { svgId: string }) {
  const [detail, setDetail] = useState<AircraftDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getAircraftDetail(svgId)
      .then(setDetail)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [svgId]);

  if (loading) {
    return <LoadingState colSpan={1} />;
  }

  if (error || !detail) {
    return (
      <div className="space-y-4">
        <PageHeader
          eyebrow="Aircraft configuration"
          title="Configuration not found"
          description={error || svgId}
        />
        <Link href="/fleet" className="text-sm text-primary hover:underline">
          Back to fleet
        </Link>
      </div>
    );
  }

  const cabinKeys = CABINS.map((c) => c.key).filter((key) => detail.cabins[key]);
  const airlineSlug = svgId.split("-", 1)[0];

  const hardwareRows: { category: string; field: string; getValue: (key: CabinKey) => unknown }[] =
    [];
  for (const field of CABIN_FIELDS) {
    hardwareRows.push({
      category: "Cabin hardware",
      field: hardwareFieldLabel(field),
      getValue: (key) => {
        const cabin = detail.cabins[key];
        return cabin ? (cabin as Record<string, unknown>)[field] : null;
      },
    });
  }
  for (const field of FLIGHT_FIELDS) {
    hardwareRows.push({
      category: "Flight features",
      field: flightFieldLabel(field),
      getValue: (key) => {
        const flight = detail.flight_features?.cabins[key];
        return flight ? (flight as Record<string, unknown>)[field] : null;
      },
    });
  }

  let lastCategory = "";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Aircraft configuration"
        title={detail.aircraft_type_displayed || detail.svg_id}
        description={detail.description || undefined}
        actions={
          <Link
            href="/fleet"
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Back to fleet
          </Link>
        }
      />

      <SectionCard title="Aircraft overview">
        <dl className="flex flex-wrap gap-x-5 gap-y-1.5 px-4 py-2.5 text-xs">
          <div className="flex items-baseline gap-1.5">
            <dt className="text-muted-foreground">Airline</dt>
            <dd>
              <AirlineBadge slug={airlineSlug} name={detail.airline_name} />
            </dd>
          </div>
          <div className="flex items-baseline gap-1.5">
            <dt className="text-muted-foreground">Config ID</dt>
            <dd className="font-mono">{detail.svg_id}</dd>
          </div>
          <div className="flex items-baseline gap-1.5">
            <dt className="text-muted-foreground">Layout</dt>
            <dd>{detail.configuration || "—"}</dd>
          </div>
          <div className="flex items-baseline gap-1.5">
            <dt className="text-muted-foreground">Total seats</dt>
            <dd className="tabular-nums">{detail.total_seats ?? "—"}</dd>
          </div>
          <div className="flex min-w-0 max-w-xs items-baseline gap-1.5">
            <dt className="shrink-0 text-muted-foreground">IFE</dt>
            <dd className="truncate">
              {[detail.ife_provider, detail.ife_system_name].filter(Boolean).join(" ") || "—"}
            </dd>
          </div>
          <div className="flex min-w-0 max-w-xs items-baseline gap-1.5">
            <dt className="shrink-0 text-muted-foreground">WiFi</dt>
            <dd className="truncate">
              {[detail.wifi_provider, detail.wifi_system_name].filter(Boolean).join(" ") || "—"}
            </dd>
          </div>
          <div className="flex items-baseline gap-1.5">
            <dt className="text-muted-foreground">AeroLOPA</dt>
            <dd>
              <a
                href={`https://www.aerolopa.com/${detail.svg_id}`}
                target="_blank"
                rel="noopener noreferrer"
                className={cn("inline-flex items-center gap-0.5 font-mono", TABLE_LINK_CLASS)}
              >
                {detail.svg_id}
                <ExternalLink className="size-2.5" aria-hidden />
              </a>
            </dd>
          </div>
          {detail.is_dual_deck && (
            <div className="flex items-baseline gap-1.5">
              <dt className="text-muted-foreground">Deck</dt>
              <dd>
                <Badge variant="secondary" className="text-[10px]">
                  Dual deck
                </Badge>
              </dd>
            </div>
          )}
        </dl>
      </SectionCard>

      <SectionCard title="Cabin comparison">
        <Table className="table-fixed">
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className={cn(TABLE_HEAD_CLASS, COMPARE_FEATURE_COLUMN_CLASS)}>
                Feature
              </TableHead>
              {cabinKeys.map((key) => (
                <TableHead
                  key={key}
                  className={cn(TABLE_HEAD_CLASS, COMPARE_AIRLINE_COLUMN_CLASS)}
                >
                  {CABINS.find((c) => c.key === key)?.label || key}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {hardwareRows.map((row) => {
              const showCategory = row.category !== lastCategory;
              lastCategory = row.category;
              return (
                <Fragment key={`${row.category}-${row.field}`}>
                  {showCategory && (
                    <TableRow className="bg-muted/50 hover:bg-muted/50">
                      <TableCell
                        colSpan={cabinKeys.length + 1}
                        className="py-1.5 text-xs font-medium"
                      >
                        {row.category}
                      </TableCell>
                    </TableRow>
                  )}
                  <TableRow className={TABLE_ROW_CLASS}>
                    <TableCell
                      className={cn("py-1.5 text-muted-foreground", COMPARE_FEATURE_COLUMN_CLASS)}
                    >
                      {row.field}
                    </TableCell>
                    {cabinKeys.map((key) => {
                      const raw = row.getValue(key as CabinKey);
                      const display =
                        row.category === "Flight features"
                          ? formatFlightValue(raw)
                          : formatCompareValue(raw);
                      return (
                        <TableCell
                          key={key}
                          className={cn("py-1.5 tabular-nums", COMPARE_AIRLINE_COLUMN_CLASS)}
                        >
                          <div className="min-w-0 text-left">
                            <span className="block whitespace-normal break-words [overflow-wrap:anywhere]">
                              {display}
                            </span>
                          </div>
                        </TableCell>
                      );
                    })}
                  </TableRow>
                </Fragment>
              );
            })}
          </TableBody>
        </Table>
      </SectionCard>
    </div>
  );
}
