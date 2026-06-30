import { Badge } from "@/components/ui/badge";
import { airlineLabelClass } from "@/lib/design-tokens";
import { cn } from "@/lib/utils";

export function AirlineBadge({ slug, name }: { slug: string; name?: string }) {
  const labelClass = airlineLabelClass(slug);
  return (
    <Badge variant="outline" className={cn(labelClass)}>
      {name || slug.toUpperCase()}
    </Badge>
  );
}
