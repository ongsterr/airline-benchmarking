"use client";

import { createContext, useContext, type ReactNode } from "react";
import { usePipelineRun } from "@/lib/use-pipeline-run";

type PipelineRunContextValue = ReturnType<typeof usePipelineRun>;

const PipelineRunContext = createContext<PipelineRunContextValue | null>(null);

export function PipelineRunProvider({ children }: { children: ReactNode }) {
  const value = usePipelineRun();
  return (
    <PipelineRunContext.Provider value={value}>{children}</PipelineRunContext.Provider>
  );
}

export function usePipelineRunContext() {
  const context = useContext(PipelineRunContext);
  if (!context) {
    throw new Error("usePipelineRunContext must be used within PipelineRunProvider");
  }
  return context;
}
