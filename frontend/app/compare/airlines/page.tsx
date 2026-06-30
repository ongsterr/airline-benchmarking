import { Suspense } from "react";
import { PageFallback } from "@/components/page-fallback";
import AirlineComparePageClient from "./airline-compare-client";

export default function AirlineComparePage() {
  return (
    <Suspense fallback={<PageFallback message="Loading airline comparison..." />}>
      <AirlineComparePageClient />
    </Suspense>
  );
}
