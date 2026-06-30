"use client";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  formatCompareValue,
  getFieldType,
  parseFieldInput,
  serializeFieldInput,
} from "@/lib/compare-fields";
import { COMPARE_EDIT_FIELD_CLASS } from "@/lib/design-tokens";
import { cn } from "@/lib/utils";

type CompareFieldInputProps = {
  fieldKey: string;
  value: unknown;
  onChange: (value: unknown) => void;
  className?: string;
};

export function CompareFieldInput({
  fieldKey,
  value,
  onChange,
  className,
}: CompareFieldInputProps) {
  const fieldType = getFieldType(fieldKey);

  if (fieldType === "bool") {
    const boolValue = value === true || value === "Yes";
    return (
      <Select
        value={boolValue ? "true" : "false"}
        onValueChange={(v) => onChange(v === "true")}
      >
        <SelectTrigger size="sm" className={cn(COMPARE_EDIT_FIELD_CLASS, className)}>
          <SelectValue className="text-xs" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="true">Yes</SelectItem>
          <SelectItem value="false">No</SelectItem>
        </SelectContent>
      </Select>
    );
  }

  const inputType = fieldType === "string" ? "text" : "number";
  const step = fieldType === "float" ? "any" : "1";

  return (
    <Input
      type={inputType}
      step={inputType === "number" ? step : undefined}
      value={serializeFieldInput(fieldKey, value)}
      onChange={(e) => onChange(parseFieldInput(fieldKey, e.target.value))}
      className={cn(COMPARE_EDIT_FIELD_CLASS, className)}
    />
  );
}

type CompareValueCellProps = {
  fieldKey: string;
  value: unknown;
  isEditing: boolean;
  isDirty: boolean;
  diff: boolean;
  canEdit?: boolean;
  onStartEdit: () => void;
  onChange: (value: unknown) => void;
};

export function CompareValueCell({
  fieldKey,
  value,
  isEditing,
  isDirty,
  diff,
  canEdit = false,
  onStartEdit,
  onChange,
}: CompareValueCellProps) {
  if (isEditing) {
    return (
      <div className={cn("relative", isDirty && "ring-1 ring-primary/40 rounded-md")}>
        <CompareFieldInput fieldKey={fieldKey} value={value} onChange={onChange} />
      </div>
    );
  }

  const display = formatCompareValue(value);

  if (!canEdit) {
    return (
      <span className={cn("block px-1 py-0.5 tabular-nums", diff && "font-medium")}>
        {diff ? (
          <Badge variant="outline" className="font-normal">
            {display}
          </Badge>
        ) : (
          display
        )}
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={onStartEdit}
      className={cn(
        "w-full rounded px-1 py-0.5 text-left transition-colors",
        "hover:bg-muted/80 hover:ring-1 hover:ring-border",
        diff && "font-medium"
      )}
      title="Click to edit this configuration"
    >
      {diff ? (
        <Badge variant="outline" className="font-normal">
          {display}
        </Badge>
      ) : (
        display
      )}
    </button>
  );
}
