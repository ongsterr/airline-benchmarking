"use client";

import Link from "next/link";
import { Fragment, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AirlineBadge } from "@/components/airline-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { LoadingState } from "@/components/loading-state";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
  TABLE_HEAD_CLASS,
  TABLE_LINK_CLASS,
  TABLE_ROW_CLASS,
  type CabinKey,
} from "@/lib/design-tokens";
import { cn } from "@/lib/utils";
import {
  CompareConfigColumn,
  CompareRow,
  getCompare,
} from "@/lib/api";

function isDifferent(values: Record<string, unknown>) {
  const vals = Object.values(values);
  return new Set(vals.map(String)).size > 1;
}

function ColumnHeader({ column }: { column: CompareConfigColumn }) {
  return (
    <div className="space-y-1">
      <AirlineBadge slug={column.airline_slug} name={column.airline_name} />
      <div className="text-xs font-medium leading-tight">
        {column.aircraft_type_displayed || column.svg_id}
      </div>
      {(column.aircraft_code_displayed || column.configuration) && (
        <div className="font-mono text-[10px] text-muted-foreground">
          {column.aircraft_code_displayed}
          {column.aircraft_code_displayed && column.configuration ? " · " : ""}
          {column.configuration}
        </div>
      )}
      <a
        href={column.source_url}
        target="_blank"
        rel="noopener noreferrer"
        className={cn("font-mono text-[10px]", TABLE_LINK_CLASS)}
      >
        {column.svg_id}
      </a>
    </div>
  );
}

export default function ComparePageClient() {
  const searchParams = useSearchParams();
  const idsParam = searchParams.get("ids") || "";
  const ids = idsParam.split(",").filter(Boolean);
  const [cabin, setCabin] = useState<CabinKey>("business");
  const [columns, setColumns] = useState<CompareConfigColumn[]>([]);
  const [rows, setRows] = useState<CompareRow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (ids.length < 2) return;
    setLoading(true);
    getCompare(ids, cabin)
      .then((data) => {
        setColumns(data.columns);
        setRows(data.rows);
      })
      .catch(() => {
        setColumns([]);
        setRows([]);
      })
      .finally(() => setLoading(false));
  }, [idsParam, cabin, ids.length]);

  if (ids.length < 2) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Configuration analysis"
          title="Configuration comparison"
          description="Select at least two configurations from the Fleet view."
        />
        <EmptyState message="Select at least 2 aircraft configurations from the Fleet view to compare." />
      </div>
    );
  }

  let lastCategory = "";

  const columnById = new Map(columns.map((c) => [c.svg_id, c]));
  const displayIds = columns.length > 0 ? columns.map((c) => c.svg_id) : ids;

  const cabinTabs = (
    <Tabs value={cabin} onValueChange={(v) => v && setCabin(v as CabinKey)}>
      <TabsList variant="line" className="h-8">
        {CABINS.map((c) => (
          <TabsTrigger key={c.key} value={c.key} className="px-2.5 text-xs">
            {c.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );

  const editUrl = `/fleet?ids=${idsParam}`;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Configuration analysis"
        title="Configuration comparison"
        description={`Comparing ${ids.length} aircraft configurations.`}
        actions={
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              render={<Link href={editUrl} />}
            >
              Edit selection
            </Button>
            {cabinTabs}
          </div>
        }
      />

      <SectionCard title="Features">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className={TABLE_HEAD_CLASS}>Feature</TableHead>
              {displayIds.map((id) => {
                const column = columnById.get(id);
                return (
                  <TableHead key={id} className={cn(TABLE_HEAD_CLASS, "min-w-36")}>
                    {column ? (
                      <ColumnHeader column={column} />
                    ) : (
                      <span className="font-mono">{id}</span>
                    )}
                  </TableHead>
                );
              })}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <LoadingState colSpan={displayIds.length + 1} />
            ) : (
              rows.map((row) => {
                const showCategory = row.category !== lastCategory;
                lastCategory = row.category;
                const diff = isDifferent(row.values);
                return (
                  <Fragment key={`${row.category}-${row.feature}`}>
                    {showCategory && (
                      <TableRow className="bg-muted/50 hover:bg-muted/50">
                        <TableCell
                          colSpan={displayIds.length + 1}
                          className="py-1.5 text-xs font-medium"
                        >
                          {row.category}
                        </TableCell>
                      </TableRow>
                    )}
                    <TableRow className={TABLE_ROW_CLASS}>
                      <TableCell className="py-1.5 text-muted-foreground">
                        {row.feature}
                      </TableCell>
                      {displayIds.map((id) => (
                        <TableCell
                          key={id}
                          className={cn(
                            "py-1.5 tabular-nums",
                            diff && "bg-muted/60"
                          )}
                        >
                          {diff ? (
                            <Badge variant="outline" className="font-normal">
                              {String(row.values[id] ?? "—")}
                            </Badge>
                          ) : (
                            String(row.values[id] ?? "—")
                          )}
                        </TableCell>
                      ))}
                    </TableRow>
                  </Fragment>
                );
              })
            )}
          </TableBody>
        </Table>
      </SectionCard>
    </div>
  );
}
