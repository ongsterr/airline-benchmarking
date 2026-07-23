"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { PipelineProgressPanel } from "@/components/pipeline-progress-panel";
import { Button } from "@/components/ui/button";
import type { MenuPipelineTriggerConfig } from "@/lib/api";
import { usePipelineRunContext } from "@/lib/pipeline-run-context";
import { cn } from "@/lib/utils";

const DEFAULT_MENU_CONFIG_JSON = `{
  "defaults": {
    "cabins": ["first", "business", "premium_economy", "economy"],
    "force": false,
    "skip_existing": true
  },
  "extractions": [
    {
      "date": "2026-08-01",
      "flight": "EK7",
      "origin": "DXB",
      "destination": "LHR"
    }
  ]
}`;

type MenuExtractSectionProps = {
  canTrigger: boolean;
  isAuthLoading: boolean;
  onSignInRequired: () => void;
  onComplete: () => void;
};

function validateMenuConfig(parsed: unknown): MenuPipelineTriggerConfig | null {
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return null;
  }
  const obj = parsed as Record<string, unknown>;
  if (!Array.isArray(obj.extractions) || obj.extractions.length === 0) {
    return null;
  }
  for (const entry of obj.extractions) {
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
      return null;
    }
    const e = entry as Record<string, unknown>;
    if (
      typeof e.date !== "string" ||
      typeof e.flight !== "string" ||
      typeof e.origin !== "string" ||
      typeof e.destination !== "string"
    ) {
      return null;
    }
  }
  return parsed as MenuPipelineTriggerConfig;
}

export function MenuExtractSection({
  canTrigger,
  isAuthLoading,
  onSignInRequired,
  onComplete,
}: MenuExtractSectionProps) {
  const [configText, setConfigText] = useState(DEFAULT_MENU_CONFIG_JSON);
  const {
    activeRun,
    lastResult,
    isRunning,
    isStarting,
    startMenu,
    clearError,
  } = usePipelineRunContext();
  const completedRunIdRef = useRef<string | null>(null);

  const parseResult = useMemo(() => {
    try {
      const parsed = JSON.parse(configText) as unknown;
      const config = validateMenuConfig(parsed);
      if (!config) {
        return {
          config: null as MenuPipelineTriggerConfig | null,
          error: "Config must include a non-empty extractions[] with date, flight, origin, destination",
        };
      }
      return { config, error: null as string | null };
    } catch {
      return {
        config: null as MenuPipelineTriggerConfig | null,
        error: "Invalid JSON",
      };
    }
  }, [configText]);

  const isBusy =
    isStarting || (isRunning && activeRun?.pipeline_type === "menu");
  const canRun = canTrigger && Boolean(parseResult.config) && !isBusy;

  const handleClick = async () => {
    if (!canTrigger) {
      onSignInRequired();
      return;
    }
    if (!parseResult.config || isBusy) return;

    clearError();
    completedRunIdRef.current = null;
    try {
      const run = await startMenu(parseResult.config);
      if (run.status !== "running") {
        completedRunIdRef.current = run.id;
        onComplete();
      }
    } catch {
      // Error surfaced via hook / progress panel.
    }
  };

  useEffect(() => {
    if (
      !lastResult ||
      lastResult.pipeline_type !== "menu" ||
      lastResult.status === "running" ||
      completedRunIdRef.current === lastResult.id
    ) {
      return;
    }
    completedRunIdRef.current = lastResult.id;
    onComplete();
  }, [lastResult, onComplete]);

  if (!isAuthLoading && !canTrigger) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2">
        <p className="text-xs text-muted-foreground">
          Sign in to run the menu pipeline.
        </p>
        <Button type="button" variant="outline" size="sm" onClick={onSignInRequired}>
          Sign in
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-2 px-4 py-2">
      <p className="text-xs text-muted-foreground">
        Paste a JSON config with <code className="text-[10px]">defaults</code>{" "}
        and <code className="text-[10px]">extractions[]</code> (same shape as{" "}
        <code className="text-[10px]">pipeline/menu_batch.example.json</code>).
      </p>
      <textarea
        value={configText}
        onChange={(e) => setConfigText(e.target.value)}
        spellCheck={false}
        aria-label="Menu extraction JSON config"
        className={cn(
          "min-h-40 w-full resize-y rounded-md border border-input bg-transparent px-3 py-2",
          "font-mono text-xs leading-relaxed shadow-xs outline-none",
          "focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]",
          "disabled:cursor-not-allowed disabled:opacity-50"
        )}
        disabled={isBusy}
      />
      {parseResult.error && (
        <p className="text-[10px] text-destructive">{parseResult.error}</p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={!canRun}
          onClick={() => void handleClick()}
        >
          {isBusy && <Loader2 className="mr-1.5 size-3.5 animate-spin" />}
          Run pipeline
        </Button>
        {parseResult.config && (
          <span className="text-[11px] text-muted-foreground">
            {parseResult.config.extractions.length} flight
            {parseResult.config.extractions.length === 1 ? "" : "s"} ready
          </span>
        )}
      </div>
      <PipelineProgressPanel onComplete={onComplete} />
    </div>
  );
}
