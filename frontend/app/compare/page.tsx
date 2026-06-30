import { Suspense } from "react";
import { PageFallback } from "@/components/page-fallback";
import ComparePageClient from "./compare-client";

export default function ComparePage() {
  return (
    <Suspense fallback={<PageFallback message="Loading comparison..." />}>
      <ComparePageClient />
    </Suspense>
  );
}
