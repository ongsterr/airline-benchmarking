"use client";

import { useMemo, useState } from "react";
import { PipelineProgressPanel } from "@/components/pipeline-progress-panel";
import { PipelineTriggerButton } from "@/components/pipeline-trigger-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { parseAirlineSlugInput, validateAirlineSlugs } from "@/lib/airline-slugs";
import { TOOLBAR_CONTROL_CLASS } from "@/lib/design-tokens";
import { cn } from "@/lib/utils";

type AirlineExtractSectionProps = {
  canTrigger: boolean;
  isAuthLoading: boolean;
  onSignInRequired: () => void;
  onComplete: () => void;
};

export function AirlineExtractSection({
  canTrigger,
  isAuthLoading,
  onSignInRequired,
  onComplete,
}: AirlineExtractSectionProps) {
  const [slugInput, setSlugInput] = useState("");

  const parsedSlugs = useMemo(() => parseAirlineSlugInput(slugInput), [slugInput]);
  const { valid: airlines, invalid } = useMemo(
    () => validateAirlineSlugs(parsedSlugs),
    [parsedSlugs]
  );
  const hasInput = parsedSlugs.length > 0;
  const canRun = canTrigger && airlines.length > 0 && invalid.length === 0;

  if (!isAuthLoading && !canTrigger) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2">
        <p className="text-xs text-muted-foreground">
          Sign in to extract or update airline data.
        </p>
        <Button type="button" variant="outline" size="sm" onClick={onSignInRequired}>
          Sign in
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-2 px-4 py-2">
      <div className="flex flex-wrap items-end gap-2">
        <div className="space-y-0.5">
          <Input
            placeholder="cx, sq, ek"
            value={slugInput}
            onChange={(e) => setSlugInput(e.target.value)}
            className={cn(TOOLBAR_CONTROL_CLASS, "w-48 font-mono")}
            autoComplete="off"
            spellCheck={false}
            aria-label="AeroLOPA airline slugs"
          />
          {hasInput && invalid.length > 0 && (
            <p className="text-[10px] text-destructive">
              Invalid: {invalid.join(", ")}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-end gap-2">
          <PipelineTriggerButton
            pipelineType="hardware"
            airlines={airlines}
            canTrigger={canRun}
            onSignInRequired={onSignInRequired}
            onComplete={onComplete}
            label="Extract hardware"
            skipExisting={false}
          />
          <PipelineTriggerButton
            pipelineType="flight"
            airlines={airlines}
            canTrigger={canRun}
            onSignInRequired={onSignInRequired}
            onComplete={onComplete}
            label="Extract flight"
            skipExisting={false}
          />
          <PipelineTriggerButton
            pipelineType="hardware"
            airlines={airlines}
            canTrigger={canRun}
            onSignInRequired={onSignInRequired}
            onComplete={onComplete}
            label="Update hardware"
            skipExisting
          />
          <PipelineTriggerButton
            pipelineType="flight"
            airlines={airlines}
            canTrigger={canRun}
            onSignInRequired={onSignInRequired}
            onComplete={onComplete}
            label="Update flight"
            skipExisting
          />
        </div>
      </div>

      <PipelineProgressPanel onComplete={onComplete} />
    </div>
  );
}
