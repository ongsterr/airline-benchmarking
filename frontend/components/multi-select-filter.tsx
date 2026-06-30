"use client";

import { ChevronDownIcon } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { CONTROL_WIDTH, TOOLBAR_CONTROL_CLASS } from "@/lib/design-tokens";
import { cn } from "@/lib/utils";

export type MultiSelectOption = {
  value: string;
  label: string;
};

type MultiSelectFilterProps = {
  emptyLabel: string;
  options: MultiSelectOption[];
  selected: string[];
  onChange: (selected: string[]) => void;
  className?: string;
};

export function MultiSelectFilter({
  emptyLabel,
  options,
  selected,
  onChange,
  className,
}: MultiSelectFilterProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

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
    if (selected.length === 0) return emptyLabel;
    if (selected.length === 1) {
      return (
        options.find((option) => option.value === selected[0])?.label ??
        selected[0]
      );
    }
    return `${selected.length} selected`;
  }, [emptyLabel, options, selected]);

  const toggle = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((item) => item !== value));
      return;
    }
    onChange([...selected, value]);
  };

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          TOOLBAR_CONTROL_CLASS,
          CONTROL_WIDTH.sm,
          "flex items-center justify-between gap-1.5 rounded-lg border border-input bg-transparent px-2.5 text-left transition-colors outline-none hover:bg-muted/40 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
        )}
      >
        <span className="min-w-0 flex-1 truncate">{displayLabel}</span>
        <ChevronDownIcon className="size-3.5 shrink-0 text-muted-foreground" />
      </button>
      {open && (
        <div
          role="listbox"
          aria-multiselectable
          className="absolute right-0 z-50 mt-1 max-h-60 w-48 overflow-y-auto rounded-lg border bg-popover p-1 text-[11px] shadow-md ring-1 ring-foreground/10"
        >
          {options.map((option) => {
            const checked = selected.includes(option.value);
            return (
              <label
                key={option.value}
                className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 hover:bg-accent"
              >
                <Checkbox
                  checked={checked}
                  onCheckedChange={() => toggle(option.value)}
                />
                <span className="min-w-0 flex-1 truncate">{option.label}</span>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}
