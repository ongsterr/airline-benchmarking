import { AirlineDashboard } from "@/components/airline-dashboard";
import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { getAirlineSummaries, type AirlineSummary } from "@/lib/api";

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

      <AirlineDashboard initialSummaries={summaries} />
    </div>
  );
}
