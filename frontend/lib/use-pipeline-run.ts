"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  getActivePipelineRun,
  getPipelineRun,
  type PipelineRun,
  type PipelineTriggerOptions,
  type PipelineType,
  triggerFlightPipeline,
  triggerHardwarePipeline,
} from "@/lib/api";

const POLL_INTERVAL_MS = 2500;

export function usePipelineRun() {
  const [activeRun, setActiveRun] = useState<PipelineRun | null>(null);
  const [lastResult, setLastResult] = useState<PipelineRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const pollRun = useCallback(
    async (runId: string) => {
      try {
        const run = await getPipelineRun(runId);
        setActiveRun(run);
        if (run.status !== "running") {
          stopPolling();
          setLastResult(run);
          setActiveRun(null);
        }
      } catch (err) {
        stopPolling();
        setError(err instanceof Error ? err.message : "Failed to check pipeline status");
        setActiveRun(null);
      }
    },
    [stopPolling]
  );

  const startPolling = useCallback(
    (runId: string) => {
      stopPolling();
      void pollRun(runId);
      pollTimerRef.current = setInterval(() => {
        void pollRun(runId);
      }, POLL_INTERVAL_MS);
    },
    [pollRun, stopPolling]
  );

  const startPipeline = useCallback(
    async (pipelineType: PipelineType, options: PipelineTriggerOptions) => {
      setError(null);
      setIsStarting(true);
      try {
        const trigger =
          pipelineType === "hardware"
            ? triggerHardwarePipeline
            : triggerFlightPipeline;
        const run = await trigger(options);
        setActiveRun(run);
        if (run.status === "running") {
          startPolling(run.id);
        } else {
          setLastResult(run);
          setActiveRun(null);
        }
        return run;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to start pipeline";
        setError(message);
        throw err;
      } finally {
        setIsStarting(false);
      }
    },
    [startPolling]
  );

  const startHardware = useCallback(
    (options: PipelineTriggerOptions) => startPipeline("hardware", options),
    [startPipeline]
  );

  const startFlight = useCallback(
    (options: PipelineTriggerOptions) => startPipeline("flight", options),
    [startPipeline]
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const run = await getActivePipelineRun();
        if (cancelled || !run) return;
        setActiveRun(run);
        if (run.status === "running") {
          startPolling(run.id);
        }
      } catch {
        // Ignore — user may not be authenticated yet.
      }
    })();
    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [startPolling, stopPolling]);

  return {
    activeRun,
    lastResult,
    error,
    isRunning: Boolean(activeRun?.status === "running"),
    isStarting,
    startHardware,
    startFlight,
    clearError: () => setError(null),
  };
}
