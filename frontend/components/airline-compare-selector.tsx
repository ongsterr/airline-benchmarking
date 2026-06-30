"use client";

import { Check } from "lucide-react";
import { AirlineBadge } from "@/components/airline-badge";
import type { AirlineSummary } from "@/lib/api";
import { MAX_COMPARE_CONFIGS, MIN_COMPARE_CONFIGS } from "@/lib/constants";
import { cn } from "@/lib/utils";

type AirlineCompareSelectorProps = {
  summaries: AirlineSummary[];
  selected: string[];
  onChange: (slugs: string[]) => void;
  loading?: boolean;
  loadError?: string | null;
  className?: string;
};

export function AirlineCompareSelector({
  summaries,
  selected,
  onChange,
  loading = false,
  loadError = null,
  className,
}: AirlineCompareSelectorProps) {
  const atMax = selected.length >= MAX_COMPARE_CONFIGS;

  const toggle = (slug: string) => {
    if (selected.includes(slug)) {
      onChange(selected.filter((s) => s !== slug));
      return;
    }
    if (atMax) return;
    onChange([...selected, slug]);
  };

  if (loading) {
    return (
      <p className={cn("text-xs text-muted-foreground", className)}>
        Loading airlines…
      </p>
    );
  }

  if (loadError) {
    return (
      <p className={cn("text-xs text-destructive", className)}>{loadError}</p>
    );
  }

  if (summaries.length === 0) {
    return (
      <p className={cn("text-xs text-muted-foreground", className)}>
        No airlines loaded — check API connection.
      </p>
    );
  }

  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex flex-wrap gap-1.5">
        {summaries.map((airline) => {
          const isSelected = selected.includes(airline.slug);
          const disabled = !isSelected && atMax;
          return (
            <button
              key={airline.slug}
              type="button"
              disabled={disabled}
              onClick={() => toggle(airline.slug)}
              aria-pressed={isSelected}
              className={cn(
                "inline-flex items-center gap-1 rounded-md border px-1 py-0.5 transition-colors",
                isSelected
                  ? "border-primary/40 bg-primary/5 ring-1 ring-primary/30"
                  : "border-transparent hover:bg-muted/60",
                disabled && "cursor-not-allowed opacity-40"
              )}
            >
              <AirlineBadge slug={airline.slug} name={airline.name} />
              {isSelected && (
                <Check className="size-3 shrink-0 text-primary" aria-hidden />
              )}
            </button>
          );
        })}
      </div>
      <p className="text-[11px] text-muted-foreground">
        {MIN_COMPARE_CONFIGS}–{MAX_COMPARE_CONFIGS} airlines · {selected.length}{" "}
        selected
      </p>
    </div>
  );
}
