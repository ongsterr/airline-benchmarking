"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { usePipelineRunContext } from "@/lib/pipeline-run-context";
import type { PipelineType } from "@/lib/api";

type PipelineTriggerButtonProps = {
  pipelineType: PipelineType;
  airlines: string[];
  canTrigger: boolean;
  onSignInRequired?: () => void;
  onComplete?: () => void;
  label?: string;
  skipExisting?: boolean;
  size?: "default" | "sm";
  variant?: "default" | "outline" | "ghost";
};

function formatAirlines(airlines: string[]) {
  return airlines.map((s) => s.toUpperCase()).join(", ");
}

function pipelineLabel(pipelineType: PipelineType) {
  return pipelineType === "hardware" ? "hardware" : "flight features";
}

function statusMessage(
  pipelineType: PipelineType,
  airlines: string[],
  updated: number,
  skipped: number,
  errorCount: number
) {
  const noun = pipelineLabel(pipelineType);
  if (errorCount > 0) {
    return `${noun} update finished with ${errorCount} error(s) for ${formatAirlines(airlines)}`;
  }
  return `Updated ${updated}, skipped ${skipped} for ${formatAirlines(airlines)}`;
}

function airlinesKey(airlines: string[]) {
  return airlines.join(",");
}

export function PipelineTriggerButton({
  pipelineType,
  airlines,
  canTrigger,
  onSignInRequired,
  onComplete,
  label,
  skipExisting = true,
  size = "sm",
  variant = "outline",
}: PipelineTriggerButtonProps) {
  const {
    activeRun,
    lastResult,
    error,
    isRunning,
    isStarting,
    startHardware,
    startFlight,
    clearError,
  } = usePipelineRunContext();
  const [localMessage, setLocalMessage] = useState<string | null>(null);
  const completedRunIdRef = useRef<string | null>(null);
  const key = airlinesKey(airlines);

  const isBusy =
    isStarting ||
    (isRunning &&
      activeRun?.pipeline_type === pipelineType &&
      airlinesKey(activeRun.airlines) === key);

  const handleClick = async () => {
    if (!canTrigger) {
      onSignInRequired?.();
      return;
    }
    if (airlines.length === 0 || isBusy) return;

    clearError();
    setLocalMessage(null);
    completedRunIdRef.current = null;
    const start = pipelineType === "hardware" ? startHardware : startFlight;

    try {
      const run = await start({ airlines, skipExisting });
      if (run.status !== "running") {
        const msg = statusMessage(
          pipelineType,
          airlines,
          run.configs_updated,
          run.configs_skipped,
          run.errors?.length ?? 0
        );
        setLocalMessage(msg);
        completedRunIdRef.current = run.id;
        onComplete?.();
      }
    } catch {
      // Error surfaced via hook.
    }
  };

  useEffect(() => {
    if (
      !lastResult ||
      lastResult.pipeline_type !== pipelineType ||
      airlinesKey(lastResult.airlines) !== key ||
      lastResult.status === "running" ||
      completedRunIdRef.current === lastResult.id
    ) {
      return;
    }

    completedRunIdRef.current = lastResult.id;
    setLocalMessage(
      statusMessage(
        pipelineType,
        airlines,
        lastResult.configs_updated,
        lastResult.configs_skipped,
        lastResult.errors?.length ?? 0
      )
    );
    onComplete?.();
  }, [lastResult, pipelineType, key, airlines, onComplete]);

  const displayMessage =
    localMessage ||
    (isBusy ? `Updating ${pipelineLabel(pipelineType)} for ${formatAirlines(airlines)}…` : null) ||
    error;

  const defaultLabel =
    pipelineType === "hardware" ? "Update hardware" : "Update flight features";

  return (
    <div className="flex flex-col items-start gap-1">
      <Button
        type="button"
        size={size}
        variant={variant}
        disabled={airlines.length === 0 || isBusy}
        onClick={() => void handleClick()}
      >
        {isBusy && <Loader2 className="mr-1.5 size-3.5 animate-spin" />}
        {label ?? defaultLabel}
      </Button>
      {displayMessage && (
        <p
          className={`max-w-xs text-xs ${error ? "text-destructive" : "text-muted-foreground"}`}
        >
          {displayMessage}
        </p>
      )}
    </div>
  );
}
