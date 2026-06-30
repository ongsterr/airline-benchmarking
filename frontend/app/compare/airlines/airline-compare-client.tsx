"use client";

import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AirlineBadge } from "@/components/airline-badge";
import { AirlineCompareSelector } from "@/components/airline-compare-selector";
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
  COMPARE_AIRLINE_COLUMN_CLASS,
  TABLE_HEAD_CLASS,
  TABLE_ROW_CLASS,
  type CabinKey,
} from "@/lib/design-tokens";
import { formatCompareValue } from "@/lib/compare-fields";
import { cn } from "@/lib/utils";
import {
  AirlineSummary,
  CompareRow,
  getAirlineCompare,
  getAirlineSummaries,
} from "@/lib/api";
import { MAX_COMPARE_CONFIGS, MIN_COMPARE_CONFIGS } from "@/lib/constants";

function parseSlugs(param: string | null): string[] {
  return param?.split(",").filter(Boolean) ?? [];
}

function isDifferent(values: Record<string, unknown>) {
  const vals = Object.values(values);
  return new Set(vals.map((v) => formatCompareValue(v))).size > 1;
}

export default function AirlineComparePageClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const slugsParam = searchParams.get("slugs") || "";
  const selectedSlugs = useMemo(() => parseSlugs(slugsParam), [slugsParam]);

  const [cabin, setCabin] = useState<CabinKey>("business");
  const [summaries, setSummaries] = useState<AirlineSummary[]>([]);
  const [summariesLoading, setSummariesLoading] = useState(true);
  const [summariesError, setSummariesError] = useState<string | null>(null);
  const [rows, setRows] = useState<CompareRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);

  useEffect(() => {
    setSummariesLoading(true);
    setSummariesError(null);
    getAirlineSummaries()
      .then(setSummaries)
      .catch((e) => {
        setSummaries([]);
        setSummariesError(
          e instanceof Error ? e.message : "Failed to load airlines"
        );
      })
      .finally(() => setSummariesLoading(false));
  }, []);

  const syncSlugs = useCallback(
    (nextSlugs: string[]) => {
      const params = new URLSearchParams(searchParams.toString());
      if (nextSlugs.length > 0) {
        params.set("slugs", nextSlugs.join(","));
      } else {
        params.delete("slugs");
      }
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const handleSlugsChange = useCallback(
    (next: string[]) => {
      syncSlugs(next.slice(0, MAX_COMPARE_CONFIGS));
    },
    [syncSlugs]
  );

  useEffect(() => {
    if (selectedSlugs.length < MIN_COMPARE_CONFIGS) {
      setRows([]);
      setCompareError(null);
      return;
    }
    setLoading(true);
    setCompareError(null);
    getAirlineCompare(selectedSlugs, cabin)
      .then((data) => setRows(data.rows))
      .catch((e) => {
        setRows([]);
        setCompareError(
          e instanceof Error ? e.message : "Failed to load comparison"
        );
      })
      .finally(() => setLoading(false));
  }, [selectedSlugs.join(","), cabin]);

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

  const selector = (
    <AirlineCompareSelector
      summaries={summaries}
      selected={selectedSlugs}
      onChange={handleSlugsChange}
      loading={summariesLoading}
      loadError={summariesError}
      className="w-full"
    />
  );

  if (selectedSlugs.length < MIN_COMPARE_CONFIGS) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Airline policy"
          title="Airline Cabin Comparison"
          description="Compare flight benefits (baggage, lounge, amenities) across airlines."
          actions={cabinTabs}
        />
        <SectionCard>{selector}</SectionCard>
        <EmptyState
          message={`Select at least ${MIN_COMPARE_CONFIGS} airlines.`}
        />
      </div>
    );
  }

  let lastCategory = "";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Airline policy"
        title="Airline Cabin Comparison"
        description={`Comparing ${selectedSlugs.length} airlines.`}
        actions={cabinTabs}
      />

      {compareError && <EmptyState message={compareError} />}

      <SectionCard title="Features">
        <div className="w-full border-b px-4 py-3">{selector}</div>
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className={TABLE_HEAD_CLASS}>Feature</TableHead>
              {selectedSlugs.map((slug) => {
                const summary = summaries.find((s) => s.slug === slug);
                return (
                  <TableHead
                    key={slug}
                    className={cn(TABLE_HEAD_CLASS, COMPARE_AIRLINE_COLUMN_CLASS)}
                  >
                    <AirlineBadge
                      slug={slug}
                      name={summary?.name || slug.toUpperCase()}
                    />
                  </TableHead>
                );
              })}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <LoadingState colSpan={selectedSlugs.length + 1} />
            ) : (
              rows.map((row) => {
                const showCategory = row.category !== lastCategory;
                lastCategory = row.category;
                const diff = isDifferent(row.values);
                return (
                  <Fragment key={`${row.category}-${row.field_key}`}>
                    {showCategory && (
                      <TableRow className="bg-muted/50 hover:bg-muted/50">
                        <TableCell
                          colSpan={selectedSlugs.length + 1}
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
                      {selectedSlugs.map((slug) => (
                        <TableCell
                          key={slug}
                          className={cn(
                            "py-1.5",
                            COMPARE_AIRLINE_COLUMN_CLASS,
                            diff && "bg-muted/60"
                          )}
                        >
                          {formatCompareValue(row.values[slug] ?? null)}
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
