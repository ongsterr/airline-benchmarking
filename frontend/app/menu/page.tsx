import { Suspense } from "react";
import { PageFallback } from "@/components/page-fallback";
import MenuPageClient from "./menu-client";

export default function MenuPage() {
  return (
    <Suspense fallback={<PageFallback message="Loading menu analysis..." />}>
      <MenuPageClient />
    </Suspense>
  );
}
