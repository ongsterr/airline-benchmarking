"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useRef } from "react";
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
    isRunning,
    isStarting,
    startHardware,
    startFlight,
    clearError,
  } = usePipelineRunContext();
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
    completedRunIdRef.current = null;
    const start = pipelineType === "hardware" ? startHardware : startFlight;

    try {
      const run = await start({ airlines, skipExisting });
      if (run.status !== "running") {
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
    onComplete?.();
  }, [lastResult, pipelineType, key, onComplete]);

  const defaultLabel =
    pipelineType === "hardware" ? "Update hardware" : "Update flight features";

  return (
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
  );
}
