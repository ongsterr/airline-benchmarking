"use client";

import type { ReactNode } from "react";
import { Input } from "@/components/ui/input";
import {
  formatFlightValue,
  getFlightFieldType,
  parseFlightFieldInput,
  serializeFlightFieldInput,
} from "@/lib/flight-fields";
import { COMPARE_EDIT_FIELD_CLASS } from "@/lib/design-tokens";
import { cn } from "@/lib/utils";

type FlightCompareFieldInputProps = {
  fieldKey: string;
  value: unknown;
  onChange: (value: unknown) => void;
  className?: string;
};

export function FlightCompareFieldInput({
  fieldKey,
  value,
  onChange,
  className,
}: FlightCompareFieldInputProps) {
  const fieldType = getFlightFieldType(fieldKey);
  const inputType = fieldType === "int" ? "number" : "text";

  return (
    <Input
      type={inputType}
      step={fieldType === "int" ? "1" : undefined}
      value={serializeFlightFieldInput(fieldKey, value)}
      onChange={(e) => onChange(parseFlightFieldInput(fieldKey, e.target.value))}
      className={cn(COMPARE_EDIT_FIELD_CLASS, className)}
      placeholder={fieldType === "list" ? "Comma-separated items" : undefined}
    />
  );
}

function DiffHighlight({
  display,
  diff,
}: {
  display: ReactNode;
  diff: boolean;
}) {
  if (!diff) return <>{display}</>;
  return (
    <span className="inline-block w-full rounded-md border border-border px-2 py-0.5 text-left font-medium">
      {display}
    </span>
  );
}

type FlightCompareValueCellProps = {
  fieldKey: string;
  value: unknown;
  isEditing: boolean;
  isDirty: boolean;
  diff: boolean;
  canEdit?: boolean;
  onStartEdit: () => void;
  onChange: (value: unknown) => void;
};

export function FlightCompareValueCell({
  fieldKey,
  value,
  isEditing,
  isDirty,
  diff,
  canEdit = false,
  onStartEdit,
  onChange,
}: FlightCompareValueCellProps) {
  if (isEditing) {
    return (
      <div className={cn("relative text-left", isDirty && "rounded-md ring-1 ring-primary/40")}>
        <FlightCompareFieldInput fieldKey={fieldKey} value={value} onChange={onChange} />
      </div>
    );
  }

  const display = formatFlightValue(value);

  if (!canEdit) {
    return (
      <span className="block text-left break-words px-1 py-0.5 [overflow-wrap:anywhere]">
        <DiffHighlight display={display} diff={diff} />
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={onStartEdit}
      className={cn(
        "w-full rounded px-1 py-0.5 text-left whitespace-normal break-words transition-colors [overflow-wrap:anywhere]",
        "hover:bg-muted/80 hover:ring-1 hover:ring-border"
      )}
      title="Click to edit this airline"
    >
      <DiffHighlight display={display} diff={diff} />
    </button>
  );
}
