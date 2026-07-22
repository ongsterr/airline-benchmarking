"use client";

import { ChevronDownIcon } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import type { MenuFlightOption } from "@/lib/api";
import { MAX_COMPARE_CONFIGS } from "@/lib/constants";
import { formatMenuFlightLabel } from "@/lib/menu-fields";
import { TOOLBAR_CONTROL_CLASS } from "@/lib/design-tokens";
import { cn } from "@/lib/utils";

type MenuFlightSelectorProps = {
  options: MenuFlightOption[];
  selected: string[];
  onChange: (selected: string[]) => void;
  className?: string;
  disabled?: boolean;
};

export function MenuFlightSelector({
  options,
  selected,
  onChange,
  className,
  disabled = false,
}: MenuFlightSelectorProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const atMax = selected.length >= MAX_COMPARE_CONFIGS;

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (rootRef.current?.contains(event.target as Node)) return;
      setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  const displayLabel = useMemo(() => {
    if (selected.length === 0) return "Select flights";
    if (selected.length === 1) {
      const option = options.find((o) => o.observation_id === selected[0]);
      return option ? formatMenuFlightLabel(option) : "1 selected";
    }
    return `${selected.length} flights selected`;
  }, [options, selected]);

  const toggle = (observationId: string) => {
    if (selected.includes(observationId)) {
      onChange(selected.filter((id) => id !== observationId));
      return;
    }
    if (atMax) return;
    onChange([...selected, observationId]);
  };

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <button
        type="button"
        disabled={disabled}
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          TOOLBAR_CONTROL_CLASS,
          "flex w-72 max-w-full items-center justify-between gap-1.5 rounded-lg border border-input bg-transparent px-2.5 text-left transition-colors outline-none hover:bg-muted/40 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-input/30"
        )}
      >
        <span className="min-w-0 flex-1 truncate">{displayLabel}</span>
        <ChevronDownIcon className="size-3.5 shrink-0 text-muted-foreground" />
      </button>
      {open && (
        <div
          role="listbox"
          aria-multiselectable
          className="absolute left-0 z-50 mt-1 max-h-72 w-80 max-w-[min(20rem,calc(100vw-3rem))] overflow-y-auto rounded-lg border bg-popover p-1 text-[11px] shadow-md ring-1 ring-foreground/10"
        >
          {options.length === 0 ? (
            <p className="px-2 py-2 text-muted-foreground">
              No flights for this cabin / item type.
            </p>
          ) : (
            options.map((option) => {
              const checked = selected.includes(option.observation_id);
              const optionDisabled = !checked && atMax;
              return (
                <label
                  key={option.observation_id}
                  className={cn(
                    "flex cursor-pointer items-start gap-2 rounded-md px-2 py-1.5 hover:bg-accent",
                    optionDisabled && "cursor-not-allowed opacity-40"
                  )}
                >
                  <Checkbox
                    checked={checked}
                    disabled={optionDisabled}
                    onCheckedChange={() => {
                      if (optionDisabled) return;
                      toggle(option.observation_id);
                    }}
                    className="mt-0.5"
                  />
                  <span className="min-w-0 flex-1 space-y-0.5">
                    <span className="block truncate font-medium">
                      {formatMenuFlightLabel(option)}
                    </span>
                    <span className="block text-muted-foreground">
                      {option.available
                        ? `${option.item_count} item${option.item_count === 1 ? "" : "s"}`
                        : "Menu unavailable"}
                    </span>
                  </span>
                </label>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
