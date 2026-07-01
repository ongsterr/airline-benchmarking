"use client";

import { Loader2, X } from "lucide-react";
import { useEffect, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { PipelineRun, PipelineType } from "@/lib/api";
import { usePipelineRunContext } from "@/lib/pipeline-run-context";
import { cn } from "@/lib/utils";

type PipelineProgressPanelProps = {
  onComplete?: () => void;
};

function pipelineTitle(pipelineType: PipelineType) {
  return pipelineType === "hardware" ? "Hardware extraction" : "Flight extraction";
}

function progressUnit(pipelineType: PipelineType) {
  return pipelineType === "hardware" ? "configs" : "airlines";
}

function formatAirlines(airlines: string[]) {
  return airlines.map((s) => s.toUpperCase()).join(", ");
}

function statusBadgeVariant(status: PipelineRun["status"]) {
  if (status === "running") return "secondary" as const;
  if (status === "failed") return "destructive" as const;
  return "outline" as const;
}

function statusLabel(status: PipelineRun["status"]) {
  if (status === "running") return "Running";
  if (status === "failed") return "Failed";
  return "Completed";
}

function runProgress(run: PipelineRun) {
  const processed = run.configs_updated + run.configs_skipped;
  const total = run.configs_discovered;
  const percent = total > 0 ? Math.min(100, Math.round((processed / total) * 100)) : 0;
  return { processed, total, percent };
}

export function PipelineProgressPanel({ onComplete }: PipelineProgressPanelProps) {
  const {
    activeRun,
    lastResult,
    error,
    isStarting,
    clearError,
    clearLastResult,
  } = usePipelineRunContext();
  const completedRunIdRef = useRef<string | null>(null);

  const run = activeRun ?? lastResult;
  const isRunning = Boolean(activeRun?.status === "running" || isStarting);
  const isFinished = Boolean(lastResult && !activeRun);

  useEffect(() => {
    if (
      !lastResult ||
      lastResult.status === "running" ||
      completedRunIdRef.current === lastResult.id
    ) {
      return;
    }

    completedRunIdRef.current = lastResult.id;
    onComplete?.();
  }, [lastResult, onComplete]);

  if (!run && !error && !isStarting) {
    return null;
  }

  const handleDismiss = () => {
    clearError();
    clearLastResult();
  };

  if (error && !run) {
    return (
      <div className="rounded-md border border-destructive/30 bg-muted/30 px-3 py-2">
        <div className="flex items-start justify-between gap-2">
          <p className="text-xs text-destructive">{error}</p>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-6 px-1.5"
            onClick={handleDismiss}
            aria-label="Dismiss error"
          >
            <X className="size-3.5" />
          </Button>
        </div>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="rounded-md border bg-muted/30 px-3 py-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="size-3.5 animate-spin" />
          Starting pipeline…
        </div>
      </div>
    );
  }

  const { processed, total, percent } = runProgress(run);
  const unit = progressUnit(run.pipeline_type);
  const discovering = isRunning && total === 0;

  return (
    <div className="rounded-md border bg-muted/30 px-3 py-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium">{pipelineTitle(run.pipeline_type)}</span>
          <Badge variant={statusBadgeVariant(run.status)}>{statusLabel(run.status)}</Badge>
          <span className="text-xs text-muted-foreground">{formatAirlines(run.airlines)}</span>
        </div>
        {isFinished && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-6 px-1.5"
            onClick={handleDismiss}
            aria-label="Dismiss progress"
          >
            <X className="size-3.5" />
          </Button>
        )}
      </div>

      <div className="mt-2 space-y-1">
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <span>
            {discovering
              ? "Discovering…"
              : `${processed} / ${total} ${unit}`}
          </span>
          {!discovering && total > 0 && (
            <span>{percent}%</span>
          )}
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-300",
              run.status === "failed" ? "bg-destructive" : "bg-primary",
              discovering && "w-1/3 animate-pulse"
            )}
            style={
              discovering
                ? undefined
                : { width: `${percent}%` }
            }
          />
        </div>
        {run.status !== "running" && (
          <p className="text-[11px] text-muted-foreground">
            Updated {run.configs_updated}, skipped {run.configs_skipped}
            {(run.errors?.length ?? 0) > 0 && `, ${run.errors!.length} error(s)`}
          </p>
        )}
        {run.errors && run.errors.length > 0 && (
          <ul className="mt-1 space-y-0.5 text-[11px] text-destructive">
            {run.errors.slice(0, 5).map((entry) => (
              <li key={entry}>{entry}</li>
            ))}
            {run.errors.length > 5 && (
              <li>…and {run.errors.length - 5} more</li>
            )}
          </ul>
        )}
        {error && (
          <p className="text-[11px] text-destructive">{error}</p>
        )}
      </div>
    </div>
  );
}
