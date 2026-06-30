import Link from "next/link";
import { AirlineBadge } from "@/components/airline-badge";
import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { EmptyTableRow } from "@/components/loading-state";
import { SectionCard } from "@/components/section-card";
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
import { getAirlineSummaries, type AirlineSummary } from "@/lib/api";
import { cn } from "@/lib/utils";

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(iso));
}

export default async function SummaryPage() {
  let summaries: AirlineSummary[] = [];
  try {
    summaries = await getAirlineSummaries();
  } catch {
    summaries = [];
  }

  const totalConfigs = summaries.reduce((s, a) => s + a.config_count, 0);
  const uniqueAircraftTypes = new Set(
    summaries.flatMap((a) => a.aircraft_types)
  ).size;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Fleet intelligence"
        title="Airline Fleet Summary"
        description="Overview Of Benchmarked Airlines And Fleet Scale."
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <MetricCard title="Airlines" value={summaries.length} />
        <MetricCard title="Configurations" value={totalConfigs} />
        <MetricCard title="Unique Aircraft Types" value={uniqueAircraftTypes} />
      </div>

      <SectionCard title="Airlines">
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
                colSpan={9}
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
      </SectionCard>
    </div>
  );
}
