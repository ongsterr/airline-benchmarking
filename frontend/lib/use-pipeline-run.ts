"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelPipelineRun,
  getActivePipelineRun,
  getPipelineRun,
  type MenuPipelineTriggerConfig,
  type PipelineRun,
  type PipelineTriggerOptions,
  triggerFlightPipeline,
  triggerHardwarePipeline,
  triggerMenuPipeline,
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

  const beginRun = useCallback(
    async (trigger: () => Promise<PipelineRun>) => {
      setError(null);
      setIsStarting(true);
      try {
        const run = await trigger();
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
        // If another run is blocking (409), surface it so the user can Cancel.
        if (message.includes("409") || message.toLowerCase().includes("already in progress")) {
          try {
            const active = await getActivePipelineRun();
            if (active?.status === "running") {
              setActiveRun(active);
              startPolling(active.id);
            }
          } catch {
            // Keep the original start error.
          }
        }
        throw err;
      } finally {
        setIsStarting(false);
      }
    },
    [startPolling]
  );

  const startHardware = useCallback(
    (options: PipelineTriggerOptions) =>
      beginRun(() => triggerHardwarePipeline(options)),
    [beginRun]
  );

  const startFlight = useCallback(
    (options: PipelineTriggerOptions) =>
      beginRun(() => triggerFlightPipeline(options)),
    [beginRun]
  );

  const startMenu = useCallback(
    (config: MenuPipelineTriggerConfig) =>
      beginRun(() => triggerMenuPipeline(config)),
    [beginRun]
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

  const clearLastResult = useCallback(() => {
    setLastResult(null);
  }, []);

  const cancelActive = useCallback(async () => {
    const runId = activeRun?.id;
    if (!runId) return null;
    setError(null);
    try {
      const run = await cancelPipelineRun(runId);
      stopPolling();
      setLastResult(run);
      setActiveRun(null);
      return run;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to cancel pipeline";
      setError(message);
      throw err;
    }
  }, [activeRun?.id, stopPolling]);

  return {
    activeRun,
    lastResult,
    error,
    isRunning: Boolean(activeRun?.status === "running"),
    isStarting,
    startHardware,
    startFlight,
    startMenu,
    cancelActive,
    clearError: () => setError(null),
    clearLastResult,
  };
}
