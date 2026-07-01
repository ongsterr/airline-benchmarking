"use client";

import Link from "next/link";
import { AirlineBadge } from "@/components/airline-badge";
import { EmptyTableRow } from "@/components/loading-state";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  TABLE_CELL_CLASS,
  TABLE_CELL_MUTED_CLASS,
  TABLE_CELL_NUMERIC_CLASS,
  TABLE_HEAD_CLASS,
  TABLE_LINK_CLASS,
  TABLE_ROW_CLASS,
} from "@/lib/design-tokens";
import type { AirlineSummary } from "@/lib/api";
import { cn } from "@/lib/utils";

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(iso));
}

type AirlineSummaryTableProps = {
  summaries: AirlineSummary[];
};

export function AirlineSummaryTable({ summaries }: AirlineSummaryTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead className={TABLE_HEAD_CLASS}>Airline</TableHead>
          <TableHead className={cn(TABLE_HEAD_CLASS, "text-right")}>
            Configurations
          </TableHead>
          <TableHead className={cn(TABLE_HEAD_CLASS, "text-right")}>
            Long Haul Aircraft
          </TableHead>
          <TableHead className={cn(TABLE_HEAD_CLASS, "text-right")}>
            Short Haul Aircraft
          </TableHead>
          <TableHead className={cn(TABLE_HEAD_CLASS, "text-right")}>
            Airbus Aircraft
          </TableHead>
          <TableHead className={cn(TABLE_HEAD_CLASS, "text-right")}>
            Boeing Aircraft
          </TableHead>
          <TableHead className={cn(TABLE_HEAD_CLASS, "text-right")}>
            Other Aircraft
          </TableHead>
          <TableHead className={TABLE_HEAD_CLASS}>Last Updated</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {summaries.length === 0 ? (
          <EmptyTableRow
            colSpan={8}
            message="No data yet. Run the pipeline to load aircraft configurations."
          />
        ) : (
          summaries.map((airline) => (
            <TableRow key={airline.slug} className={TABLE_ROW_CLASS}>
              <TableCell className={TABLE_CELL_CLASS}>
                <Link
                  href={`/fleet?airline=${airline.slug}`}
                  className={cn("flex items-center gap-2", TABLE_LINK_CLASS)}
                >
                  <AirlineBadge slug={airline.slug} name={airline.name} />
                </Link>
              </TableCell>
              <TableCell className={TABLE_CELL_NUMERIC_CLASS}>
                {airline.config_count}
              </TableCell>
              <TableCell className={TABLE_CELL_NUMERIC_CLASS}>
                {airline.long_haul_count}
              </TableCell>
              <TableCell className={TABLE_CELL_NUMERIC_CLASS}>
                {airline.short_haul_count}
              </TableCell>
              <TableCell className={TABLE_CELL_NUMERIC_CLASS}>
                {airline.airbus_count}
              </TableCell>
              <TableCell className={TABLE_CELL_NUMERIC_CLASS}>
                {airline.boeing_count}
              </TableCell>
              <TableCell className={TABLE_CELL_NUMERIC_CLASS}>
                {airline.other_aircraft_count}
              </TableCell>
              <TableCell className={TABLE_CELL_MUTED_CLASS}>
                {formatDate(airline.last_pipeline_update)}
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}
