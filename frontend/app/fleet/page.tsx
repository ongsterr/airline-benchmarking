import { Suspense } from "react";
import { PageFallback } from "@/components/page-fallback";
import FleetPageClient from "./fleet-client";

export default function FleetPage() {
  return (
    <Suspense fallback={<PageFallback message="Loading fleet..." />}>
      <FleetPageClient />
    </Suspense>
  );
}
