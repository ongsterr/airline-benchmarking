'use client'

import type { ReactNode } from 'react'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { formatCompareValue, getFieldType, parseFieldInput, serializeFieldInput } from '@/lib/compare-fields'
import { COMPARE_EDIT_FIELD_CLASS } from '@/lib/design-tokens'
import { cn } from '@/lib/utils'

type CompareFieldInputProps = {
	fieldKey: string
	value: unknown
	onChange: (value: unknown) => void
	className?: string
}

export function CompareFieldInput({ fieldKey, value, onChange, className }: CompareFieldInputProps) {
	const fieldType = getFieldType(fieldKey)

	if (fieldType === 'bool') {
		const boolValue = value === true || value === 'Yes'
		return (
			<Select value={boolValue ? 'true' : 'false'} onValueChange={(v) => onChange(v === 'true')}>
				<SelectTrigger size="sm" className={cn(COMPARE_EDIT_FIELD_CLASS, className)}>
					<SelectValue className="text-xs" />
				</SelectTrigger>
				<SelectContent>
					<SelectItem value="true">Yes</SelectItem>
					<SelectItem value="false">No</SelectItem>
				</SelectContent>
			</Select>
		)
	}

	const inputType = fieldType === 'string' ? 'text' : 'number'
	const step = fieldType === 'float' ? 'any' : '1'

	return (
		<Input
			type={inputType}
			step={inputType === 'number' ? step : undefined}
			value={serializeFieldInput(fieldKey, value)}
			onChange={(e) => onChange(parseFieldInput(fieldKey, e.target.value))}
			className={cn(COMPARE_EDIT_FIELD_CLASS, className)}
		/>
	)
}

function DiffHighlight({
	display,
	diff,
}: {
	display: ReactNode
	diff: boolean
}) {
	if (!diff) return <>{display}</>
	return (
		<span className="inline-block w-full rounded-md border border-border px-2 py-0.5 text-left font-medium whitespace-normal break-words [overflow-wrap:anywhere]">
			{display}
		</span>
	)
}

type CompareValueCellProps = {
	fieldKey: string
	value: unknown
	isEditing: boolean
	isDirty: boolean
	diff: boolean
	canEdit?: boolean
	onStartEdit: () => void
	onChange: (value: unknown) => void
}

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
			<div className={cn('relative text-left', isDirty && 'rounded-md ring-1 ring-primary/40')}>
				<CompareFieldInput fieldKey={fieldKey} value={value} onChange={onChange} />
			</div>
		)
	}

	const display = formatCompareValue(value)

	if (!canEdit) {
		return (
			<span className="block px-1 py-0.5 text-left tabular-nums whitespace-normal break-words [overflow-wrap:anywhere]">
				<DiffHighlight display={display} diff={diff} />
			</span>
		)
	}

	return (
		<button
			type="button"
			onClick={onStartEdit}
			className={cn(
				'w-full rounded px-1 py-0.5 text-left whitespace-normal break-words transition-colors [overflow-wrap:anywhere]',
				'hover:bg-muted/80 hover:ring-1 hover:ring-border'
			)}
			title="Click to edit this configuration"
		>
			<DiffHighlight display={display} diff={diff} />
		</button>
	)
}
