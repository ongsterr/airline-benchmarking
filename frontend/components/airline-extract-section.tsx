"use client";

import { useMemo, useState } from "react";
import { PipelineTriggerButton } from "@/components/pipeline-trigger-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TOOLBAR_CONTROL_CLASS } from "@/lib/design-tokens";
import { cn } from "@/lib/utils";

const SLUG_PATTERN = /^[a-z0-9-]{2,20}$/;

function normalizeSlug(value: string) {
  return value.trim().toLowerCase();
}

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

  const slug = useMemo(() => normalizeSlug(slugInput), [slugInput]);
  const slugValid = slug.length > 0 && SLUG_PATTERN.test(slug);
  const slugInvalid = slug.length > 0 && !slugValid;
  const airlines = slugValid ? [slug] : [];
  const canRun = canTrigger && slugValid;

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
    <div className="space-y-1.5 px-4 py-2">
      <div className="flex flex-wrap items-end gap-2">
        <div className="space-y-0.5">
          <Input
            placeholder="Slug (e.g. cx)"
            value={slugInput}
            onChange={(e) => setSlugInput(e.target.value)}
            className={cn(TOOLBAR_CONTROL_CLASS, "w-28 font-mono")}
            autoComplete="off"
            spellCheck={false}
            aria-label="AeroLOPA airline slug"
          />
          {slugInvalid && (
            <p className="text-[10px] text-destructive">Invalid slug</p>
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
    </div>
  );
}
