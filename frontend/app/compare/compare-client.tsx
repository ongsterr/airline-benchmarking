"use client";

import { Fragment, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
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
  TABLE_ROW_CLASS,
  type CabinKey,
} from "@/lib/design-tokens";
import { cn } from "@/lib/utils";
import { CompareRow, getCompare } from "@/lib/api";

function isDifferent(values: Record<string, unknown>) {
  const vals = Object.values(values);
  return new Set(vals.map(String)).size > 1;
}

export default function ComparePageClient() {
  const searchParams = useSearchParams();
  const idsParam = searchParams.get("ids") || "";
  const ids = idsParam.split(",").filter(Boolean);
  const [cabin, setCabin] = useState<CabinKey>("business");
  const [rows, setRows] = useState<CompareRow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (ids.length < 2) return;
    setLoading(true);
    getCompare(ids, cabin)
      .then(setRows)
      .catch(() => setRows([]))
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

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Configuration analysis"
        title="Configuration comparison"
        description={`Comparing ${ids.length} aircraft configurations.`}
        actions={cabinTabs}
      />

      <SectionCard title="Features">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className={TABLE_HEAD_CLASS}>Feature</TableHead>
              {ids.map((id) => (
                <TableHead key={id} className={cn(TABLE_HEAD_CLASS, "font-mono")}>
                  {id}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <LoadingState colSpan={ids.length + 1} />
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
                          colSpan={ids.length + 1}
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
                      {ids.map((id) => (
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
