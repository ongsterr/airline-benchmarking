import AircraftDetailClient from "./aircraft-detail-client";

export default async function AircraftDetailPage({
  params,
}: {
  params: Promise<{ svg_id: string }>;
}) {
  const { svg_id } = await params;
  return <AircraftDetailClient svgId={svg_id} />;
}
