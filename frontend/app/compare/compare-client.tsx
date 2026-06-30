"use client";

import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { Fragment, useEffect, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/components/ui/dialog";
import { AirlineBadge } from "@/components/airline-badge";
import { Badge } from "@/components/ui/badge";
import { CompareValueCell } from "@/components/compare-column-editor";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/empty-state";
import { LoadingState } from "@/components/loading-state";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  CABINS,
  TABLE_HEAD_CLASS,
  TABLE_LINK_CLASS,
  TABLE_ROW_CLASS,
  type CabinKey,
} from "@/lib/design-tokens";
import { formatCompareValue, valuesEqual } from "@/lib/compare-fields";
import { cn } from "@/lib/utils";
import { useEditAuth } from "@/lib/use-edit-auth";
import {
  CompareConfigColumn,
  CompareRow,
  getCompare,
  updateAircraftConfig,
} from "@/lib/api";

type DraftValues = Record<string, unknown>;

function isDifferent(values: Record<string, unknown>) {
  const vals = Object.values(values);
  return new Set(vals.map((v) => formatCompareValue(v))).size > 1;
}

function buildDraftFromRows(rows: CompareRow[], svgId: string): DraftValues {
  const draft: DraftValues = {};
  for (const row of rows) {
    draft[row.field_key] = row.values[svgId] ?? null;
  }
  return draft;
}

function buildUpdatePayload(
  rows: CompareRow[],
  svgId: string,
  draft: DraftValues,
  cabinKey: CabinKey
): {
  aircraft: Record<string, string | number | boolean | null>;
  cabins?: Record<string, Record<string, string | number | boolean | null>>;
} {
  const aircraft: Record<string, string | number | boolean | null> = {};
  const cabin: Record<string, string | number | boolean | null> = {};

  for (const row of rows) {
    const initial = row.values[svgId] ?? null;
    const next = draft[row.field_key] ?? null;
    if (valuesEqual(initial, next)) continue;

    const typedNext = next as string | number | boolean | null;
    if (row.scope === "aircraft") {
      aircraft[row.field_key] = typedNext;
    } else {
      cabin[row.field_key] = typedNext;
    }
  }

  const cabins =
    Object.keys(cabin).length > 0 ? { [cabinKey]: cabin } : undefined;

  return { aircraft, cabins };
}

function ColumnHeader({
  column,
  isEditing,
  isDirty,
  saving,
  error,
  canEdit,
  onEdit,
  onSave,
  onCancel,
}: {
  column: CompareConfigColumn;
  isEditing: boolean;
  isDirty: boolean;
  saving: boolean;
  error: string | null;
  canEdit: boolean;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="space-y-1.5">
      <AirlineBadge slug={column.airline_slug} name={column.airline_name} />
      <div className="text-xs font-medium leading-tight">
        {column.aircraft_type_displayed || column.svg_id}
      </div>
      {(column.aircraft_code_displayed || column.configuration) && (
        <div className="font-mono text-[10px] text-muted-foreground">
          {column.aircraft_code_displayed}
          {column.aircraft_code_displayed && column.configuration ? " · " : ""}
          {column.configuration}
        </div>
      )}
      <a
        href={column.source_url}
        target="_blank"
        rel="noopener noreferrer"
        className={cn(
          "inline-flex items-center gap-0.5 font-mono text-[10px]",
          TABLE_LINK_CLASS
        )}
        title="Open on AeroLOPA (new tab)"
      >
        {column.svg_id}
        <ExternalLink className="size-2.5 shrink-0 opacity-70" aria-hidden />
      </a>
      <div className="flex flex-wrap items-center gap-1 pt-0.5 pb-2">
        {canEdit &&
          (isEditing ? (
            <>
              <Button
                size="sm"
                className="h-6 px-2 text-[10px]"
                disabled={!isDirty || saving}
                onClick={onSave}
              >
                {saving ? "Saving…" : "Save"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-6 px-2 text-[10px]"
                disabled={saving}
                onClick={onCancel}
              >
                Cancel
              </Button>
            </>
          ) : (
            <Button
              variant="outline"
              size="sm"
              className="h-6 px-2 text-[10px]"
              onClick={onEdit}
            >
              Edit
            </Button>
          ))}
      </div>
      {error && (
        <p className="text-[10px] text-destructive leading-tight">{error}</p>
      )}
    </div>
  );
}

export default function ComparePageClient() {
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading: authLoading, login, logout } = useEditAuth();
  const canEdit = isAuthenticated;
  const idsParam = searchParams.get("ids") || "";
  const ids = idsParam.split(",").filter(Boolean);
  const [cabin, setCabin] = useState<CabinKey>("business");
  const [columns, setColumns] = useState<CompareConfigColumn[]>([]);
  const [rows, setRows] = useState<CompareRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingSvgId, setEditingSvgId] = useState<string | null>(null);
  const [draft, setDraft] = useState<DraftValues>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [signInOpen, setSignInOpen] = useState(false);
  const [signInPassword, setSignInPassword] = useState("");
  const [signInError, setSignInError] = useState<string | null>(null);
  const [signingIn, setSigningIn] = useState(false);

  useEffect(() => {
    const idList = idsParam.split(",").filter(Boolean);
    if (idList.length < 2) {
      setColumns([]);
      setRows([]);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

    getCompare(idList, cabin)
      .then((data) => {
        if (!cancelled) {
          setColumns(data.columns);
          setRows(data.rows);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setColumns([]);
          setRows([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [idsParam, cabin]);

  useEffect(() => {
    setEditingSvgId(null);
    setDraft({});
    setSaveError(null);
  }, [cabin, idsParam]);

  useEffect(() => {
    if (!editingSvgId) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setEditingSvgId(null);
        setDraft({});
        setSaveError(null);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [editingSvgId]);

  const startEditing = (svgId: string) => {
    if (!canEdit) return;
    setEditingSvgId(svgId);
    setDraft(buildDraftFromRows(rows, svgId));
    setSaveError(null);
  };

  const cancelEditing = () => {
    setEditingSvgId(null);
    setDraft({});
    setSaveError(null);
  };

  const isDirty = useMemo(() => {
    if (!editingSvgId) return false;
    return rows.some((row) => {
      const initial = row.values[editingSvgId] ?? null;
      const next = draft[row.field_key] ?? null;
      return !valuesEqual(initial, next);
    });
  }, [draft, editingSvgId, rows]);

  const handleSave = async () => {
    if (!editingSvgId || !isDirty) return;
    const { aircraft, cabins } = buildUpdatePayload(
      rows,
      editingSvgId,
      draft,
      cabin
    );
    if (
      Object.keys(aircraft).length === 0 &&
      (!cabins || Object.keys(cabins[cabin] ?? {}).length === 0)
    ) {
      return;
    }

    setSaving(true);
    setSaveError(null);
    try {
      await updateAircraftConfig(editingSvgId, { aircraft, cabins });
      setEditingSvgId(null);
      setDraft({});
      const idList = idsParam.split(",").filter(Boolean);
      const data = await getCompare(idList, cabin);
      setColumns(data.columns);
      setRows(data.rows);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save changes");
    } finally {
      setSaving(false);
    }
  };

  const handleSignIn = async (e: FormEvent) => {
    e.preventDefault();
    setSigningIn(true);
    setSignInError(null);
    try {
      await login(signInPassword);
      setSignInOpen(false);
      setSignInPassword("");
    } catch (err) {
      setSignInError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setSigningIn(false);
    }
  };

  const handleSignOut = async () => {
    if (editingSvgId) {
      cancelEditing();
    }
    await logout();
  };

  if (ids.length < 2) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Configuration analysis"
          title="Configuration comparison"
          description="Select at least two configurations from the Fleet view."
        />
        <EmptyState message="Select at least 2 aircraft configurations from the Fleet view to compare." />
      </div>
    );
  }

  let lastCategory = "";

  const columnById = new Map(columns.map((c) => [c.svg_id, c]));
  const displayIds = columns.length > 0 ? columns.map((c) => c.svg_id) : ids;

  const cabinTabs = (
    <Tabs value={cabin} onValueChange={(v) => v && setCabin(v as CabinKey)}>
      <TabsList variant="line" className="h-8">
        {CABINS.map((c) => (
          <TabsTrigger key={c.key} value={c.key} className="px-2.5 text-xs">
            {c.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );

  const editUrl = `/fleet?ids=${idsParam}`;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Configuration analysis"
        title="Configuration comparison"
        description={`Comparing ${ids.length} aircraft configurations.`}
        actions={
          <div className="flex items-center gap-3">
            {!authLoading &&
              (canEdit ? (
                <Button variant="outline" size="sm" onClick={handleSignOut}>
                  Sign out
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSignInError(null);
                    setSignInOpen(true);
                  }}
                >
                  Sign in to edit
                </Button>
              ))}
            <Button
              variant="outline"
              size="sm"
              nativeButton={false}
              render={<Link href={editUrl} />}
            >
              Edit selection
            </Button>
            {cabinTabs}
          </div>
        }
      />

      <SectionCard title="Features">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className={TABLE_HEAD_CLASS}>Feature</TableHead>
              {displayIds.map((id) => {
                const column = columnById.get(id);
                const isEditing = editingSvgId === id;
                return (
                  <TableHead
                    key={id}
                    className={cn(
                      TABLE_HEAD_CLASS,
                      "min-w-36 align-top",
                      isEditing && "bg-primary/5 ring-1 ring-inset ring-primary/20"
                    )}
                  >
                    {column ? (
                      <ColumnHeader
                        column={column}
                        isEditing={isEditing}
                        isDirty={isDirty}
                        saving={saving}
                        error={isEditing ? saveError : null}
                        canEdit={canEdit}
                        onEdit={() => startEditing(id)}
                        onSave={handleSave}
                        onCancel={cancelEditing}
                      />
                    ) : (
                      <span className="font-mono">{id}</span>
                    )}
                  </TableHead>
                );
              })}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <LoadingState colSpan={displayIds.length + 1} />
            ) : (
              rows.map((row) => {
                const showCategory = row.category !== lastCategory;
                lastCategory = row.category;
                const diff = isDifferent(row.values);
                return (
                  <Fragment key={`${row.category}-${row.field_key}`}>
                    {showCategory && (
                      <TableRow className="bg-muted/50 hover:bg-muted/50">
                        <TableCell
                          colSpan={displayIds.length + 1}
                          className="py-1.5 text-xs font-medium"
                        >
                          {row.category}
                        </TableCell>
                      </TableRow>
                    )}
                    <TableRow className={TABLE_ROW_CLASS}>
                      <TableCell className="py-1.5 text-muted-foreground">
                        {row.feature}
                      </TableCell>
                      {displayIds.map((id) => {
                        const isEditing = editingSvgId === id;
                        const cellValue = isEditing
                          ? (draft[row.field_key] ?? null)
                          : (row.values[id] ?? null);
                        const initialValue = row.values[id] ?? null;
                        const isCellDirty =
                          isEditing &&
                          !valuesEqual(initialValue, draft[row.field_key] ?? null);

                        return (
                          <TableCell
                            key={id}
                            className={cn(
                              "py-1.5 tabular-nums",
                              diff && !isEditing && "bg-muted/60",
                              isEditing && "bg-primary/5"
                            )}
                          >
                            {isEditing ? (
                              <CompareValueCell
                                fieldKey={row.field_key}
                                value={cellValue}
                                isEditing
                                isDirty={isCellDirty}
                                diff={diff}
                                canEdit={canEdit}
                                onStartEdit={() => startEditing(id)}
                                onChange={(value) =>
                                  setDraft((prev) => ({
                                    ...prev,
                                    [row.field_key]: value,
                                  }))
                                }
                              />
                            ) : (
                              <CompareValueCell
                                fieldKey={row.field_key}
                                value={cellValue}
                                isEditing={false}
                                isDirty={false}
                                diff={diff}
                                canEdit={canEdit}
                                onStartEdit={() => startEditing(id)}
                                onChange={() => {}}
                              />
                            )}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  </Fragment>
                );
              })
            )}
          </TableBody>
        </Table>
      </SectionCard>

      <Dialog open={signInOpen} onOpenChange={setSignInOpen}>
        <DialogPopup>
          <form onSubmit={handleSignIn}>
            <DialogHeader>
              <DialogTitle>Sign in to edit</DialogTitle>
              <DialogDescription>
                Enter the edit password to modify comparison fields.
              </DialogDescription>
            </DialogHeader>
            <div className="py-4">
              <Input
                type="password"
                placeholder="Password"
                value={signInPassword}
                onChange={(e) => setSignInPassword(e.target.value)}
                autoComplete="current-password"
                autoFocus
              />
              {signInError && (
                <p className="mt-2 text-sm text-destructive">{signInError}</p>
              )}
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setSignInOpen(false)}
                disabled={signingIn}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={signingIn || !signInPassword}>
                {signingIn ? "Signing in…" : "Sign in"}
              </Button>
            </DialogFooter>
          </form>
        </DialogPopup>
      </Dialog>
    </div>
  );
}
