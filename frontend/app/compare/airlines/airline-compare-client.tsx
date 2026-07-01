"use client";

import { ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import { Fragment, useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AirlineBadge } from "@/components/airline-badge";
import { AirlineCompareSelector } from "@/components/airline-compare-selector";
import { FlightCompareValueCell } from "@/components/flight-compare-cell";
import { SignInDialog } from "@/components/sign-in-dialog";
import { EmptyState } from "@/components/empty-state";
import { LoadingState } from "@/components/loading-state";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { Button } from "@/components/ui/button";
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
  COMPARE_AIRLINE_COLUMN_CLASS,
  COMPARE_FEATURE_COLUMN_CLASS,
  COMPARE_TABLE_HEAD_STICKY_CLASS,
  TABLE_HEAD_CLASS,
  TABLE_LINK_CLASS,
  TABLE_ROW_CLASS,
  type CabinKey,
} from "@/lib/design-tokens";
import {
  flightValuesEqual,
  formatFlightValue,
  normalizeReferenceSources,
  referenceSourcesDisplayKey,
} from "@/lib/flight-fields";
import { cn } from "@/lib/utils";
import { useEditAuth } from "@/lib/use-edit-auth";
import {
  AirlineSummary,
  CompareRow,
  getAirlineCompare,
  getAirlineSummaries,
  updateAirlineFlightFeatures,
} from "@/lib/api";
import { MAX_COMPARE_CONFIGS, MIN_COMPARE_CONFIGS, isDisplayAirlineSlug } from "@/lib/constants";

type DraftValues = Record<string, unknown>;

function parseSlugs(param: string | null): string[] {
  return (param?.split(",").filter(Boolean) ?? []).filter(isDisplayAirlineSlug);
}

function isDifferent(fieldKey: string, values: Record<string, unknown>) {
  const vals = Object.values(values);
  const formatter =
    fieldKey === "source_url" ? referenceSourcesDisplayKey : formatFlightValue;
  return new Set(vals.map((v) => formatter(v))).size > 1;
}

function buildDraftFromRows(rows: CompareRow[], slug: string): DraftValues {
  const draft: DraftValues = {};
  for (const row of rows) {
    if (row.scope !== "flight" || row.field_key === "source_url") continue;
    draft[row.field_key] = row.values[slug] ?? null;
  }
  return draft;
}

function buildAirlineUpdatePayload(
  rows: CompareRow[],
  slug: string,
  draft: DraftValues
): { fields: Record<string, string | number | string[] | null> } {
  const fields: Record<string, string | number | string[] | null> = {};

  for (const row of rows) {
    if (row.scope !== "flight" || row.field_key === "source_url") continue;
    const initial = row.values[slug] ?? null;
    const next = draft[row.field_key] ?? null;
    if (flightValuesEqual(row.field_key, initial, next)) continue;
    fields[row.field_key] =
      next === "—" ? null : (next as string | number | string[] | null);
  }

  return { fields };
}

function AirlineColumnHeader({
  slug,
  name,
  isEditing,
  isDirty,
  saving,
  error,
  canEdit,
  onEdit,
  onSave,
  onCancel,
}: {
  slug: string;
  name: string;
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
      <AirlineBadge slug={slug} name={name} />
      <div className="flex flex-wrap items-center gap-1 pb-1">
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
        <p className="text-[10px] leading-tight text-destructive">{error}</p>
      )}
    </div>
  );
}

function ReferenceUrlLink({
  source,
  diff,
}: {
  source: ReturnType<typeof normalizeReferenceSources>[number];
  diff: boolean;
}) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "flex items-start gap-0.5 break-all text-xs",
        TABLE_LINK_CLASS,
        diff && "font-medium"
      )}
      title={source.url}
    >
      <span className="min-w-0 flex-1">{source.title?.trim() || source.url}</span>
      <ExternalLink className="mt-0.5 size-2.5 shrink-0 opacity-70" aria-hidden />
    </a>
  );
}

function ReferenceUrlCell({ value, diff }: { value: unknown; diff: boolean }) {
  const sources = normalizeReferenceSources(value);
  if (sources.length === 0) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }

  if (sources.length === 1) {
    return <ReferenceUrlLink source={sources[0]} diff={diff} />;
  }

  const label = `${sources.length} reference URLs`;

  return (
    <details className="group">
      <summary
        className={cn(
          "flex cursor-pointer list-none items-center gap-1 text-xs text-muted-foreground hover:text-foreground [&::-webkit-details-marker]:hidden",
          diff && "font-medium text-foreground"
        )}
      >
        <ChevronRight
          className="size-3 shrink-0 group-open:hidden"
          aria-hidden
        />
        <ChevronDown
          className="hidden size-3 shrink-0 group-open:block"
          aria-hidden
        />
        <span>{label}</span>
      </summary>
      <div className="mt-1 space-y-1">
        {sources.map((source) => (
          <ReferenceUrlLink key={source.url} source={source} diff={diff} />
        ))}
      </div>
    </details>
  );
}

export default function AirlineComparePageClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading: authLoading, login, logout } = useEditAuth();
  const canEdit = isAuthenticated;

  const slugsParam = searchParams.get("slugs") || "";
  const selectedSlugs = useMemo(() => parseSlugs(slugsParam), [slugsParam]);

  const [cabin, setCabin] = useState<CabinKey>("business");
  const [summaries, setSummaries] = useState<AirlineSummary[]>([]);
  const [summariesLoading, setSummariesLoading] = useState(true);
  const [summariesError, setSummariesError] = useState<string | null>(null);
  const [rows, setRows] = useState<CompareRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);
  const [editingSlug, setEditingSlug] = useState<string | null>(null);
  const [draft, setDraft] = useState<DraftValues>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [signInOpen, setSignInOpen] = useState(false);
  const [signInPassword, setSignInPassword] = useState("");
  const [signInError, setSignInError] = useState<string | null>(null);
  const [signingIn, setSigningIn] = useState(false);

  const loadCompare = useCallback(() => {
    if (selectedSlugs.length < MIN_COMPARE_CONFIGS) {
      setRows([]);
      setCompareError(null);
      return Promise.resolve();
    }
    setLoading(true);
    setCompareError(null);
    return getAirlineCompare(selectedSlugs, cabin)
      .then((data) => setRows(data.rows))
      .catch((e) => {
        setRows([]);
        setCompareError(
          e instanceof Error ? e.message : "Failed to load comparison"
        );
      })
      .finally(() => setLoading(false));
  }, [selectedSlugs.join(","), cabin]);

  useEffect(() => {
    setSummariesLoading(true);
    setSummariesError(null);
    getAirlineSummaries()
      .then(setSummaries)
      .catch((e) => {
        setSummaries([]);
        setSummariesError(
          e instanceof Error ? e.message : "Failed to load airlines"
        );
      })
      .finally(() => setSummariesLoading(false));
  }, []);

  useEffect(() => {
    void loadCompare();
  }, [loadCompare]);

  useEffect(() => {
    setEditingSlug(null);
    setDraft({});
    setSaveError(null);
  }, [cabin, slugsParam]);

  useEffect(() => {
    if (!editingSlug) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setEditingSlug(null);
        setDraft({});
        setSaveError(null);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [editingSlug]);

  const syncSlugs = useCallback(
    (nextSlugs: string[]) => {
      const params = new URLSearchParams(searchParams.toString());
      if (nextSlugs.length > 0) {
        params.set("slugs", nextSlugs.join(","));
      } else {
        params.delete("slugs");
      }
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const handleSlugsChange = useCallback(
    (next: string[]) => {
      syncSlugs(next.slice(0, MAX_COMPARE_CONFIGS));
    },
    [syncSlugs]
  );

  const startEditing = (slug: string) => {
    if (!canEdit) return;
    setEditingSlug(slug);
    setDraft(buildDraftFromRows(rows, slug));
    setSaveError(null);
  };

  const cancelEditing = () => {
    setEditingSlug(null);
    setDraft({});
    setSaveError(null);
  };

  const isDirty = useMemo(() => {
    if (!editingSlug) return false;
    return rows.some((row) => {
      if (row.scope !== "flight" || row.field_key === "source_url") return false;
      const initial = row.values[editingSlug] ?? null;
      const next = draft[row.field_key] ?? null;
      return !flightValuesEqual(row.field_key, initial, next);
    });
  }, [draft, editingSlug, rows]);

  const handleSave = async () => {
    if (!editingSlug || !isDirty) return;
    const payload = buildAirlineUpdatePayload(rows, editingSlug, draft);
    if (Object.keys(payload.fields).length === 0) {
      return;
    }

    setSaving(true);
    setSaveError(null);
    try {
      await updateAirlineFlightFeatures(editingSlug, cabin, payload);
      setEditingSlug(null);
      setDraft({});
      await loadCompare();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Failed to save");
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
    cancelEditing();
    await logout();
  };

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

  const authActions = !authLoading && (
    canEdit ? (
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
    )
  );

  const selector = (
    <AirlineCompareSelector
      summaries={summaries}
      selected={selectedSlugs}
      onChange={handleSlugsChange}
      loading={summariesLoading}
      loadError={summariesError}
      className="w-full"
    />
  );

  const filterCard = (
    <SectionCard title="Airlines">
      <div className="px-4 py-3">{selector}</div>
    </SectionCard>
  );

  if (selectedSlugs.length < MIN_COMPARE_CONFIGS) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Airline policy"
          title="Airline Cabin Comparison"
          description="Compare flight benefits (baggage, lounge, amenities) across airlines."
          actions={
            <div className="flex items-center gap-2">
              {authActions}
              {cabinTabs}
            </div>
          }
        />
        {filterCard}
        <EmptyState
          message={`Select at least ${MIN_COMPARE_CONFIGS} airlines.`}
        />
        <SignInDialog
          open={signInOpen}
          onOpenChange={setSignInOpen}
          password={signInPassword}
          onPasswordChange={setSignInPassword}
          error={signInError}
          signingIn={signingIn}
          onSubmit={handleSignIn}
        />
      </div>
    );
  }

  let lastCategory = "";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Airline policy"
        title="Airline Cabin Comparison"
        description={`Comparing ${selectedSlugs.length} airlines.`}
        actions={
          <div className="flex items-center gap-2">
            {authActions}
            {cabinTabs}
          </div>
        }
      />

      {filterCard}

      {compareError && <EmptyState message={compareError} />}

      <SectionCard title="Features" overflowVisible>
        <Table className="table-fixed" containerClassName="overflow-visible">
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className={cn(TABLE_HEAD_CLASS, COMPARE_FEATURE_COLUMN_CLASS, COMPARE_TABLE_HEAD_STICKY_CLASS)}>
                Feature
              </TableHead>
              {selectedSlugs.map((slug) => {
                const summary = summaries.find((s) => s.slug === slug);
                const isEditing = editingSlug === slug;
                return (
                  <TableHead
                    key={slug}
                    className={cn(
                      TABLE_HEAD_CLASS,
                      COMPARE_AIRLINE_COLUMN_CLASS,
                      COMPARE_TABLE_HEAD_STICKY_CLASS,
                      isEditing && "bg-primary/5 ring-1 ring-inset ring-primary/20"
                    )}
                  >
                    <div className="min-w-0">
                    <AirlineColumnHeader
                      slug={slug}
                      name={summary?.name || slug.toUpperCase()}
                      isEditing={isEditing}
                      isDirty={isDirty}
                      saving={saving}
                      error={isEditing ? saveError : null}
                      canEdit={canEdit}
                      onEdit={() => startEditing(slug)}
                      onSave={handleSave}
                      onCancel={cancelEditing}
                    />
                    </div>
                  </TableHead>
                );
              })}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <LoadingState colSpan={selectedSlugs.length + 1} />
            ) : (
              rows.map((row) => {
                const showCategory = row.category !== lastCategory;
                lastCategory = row.category;
                const diff = isDifferent(row.field_key, row.values);
                return (
                  <Fragment key={`${row.category}-${row.field_key}`}>
                    {showCategory && (
                      <TableRow className="bg-muted/50 hover:bg-muted/50">
                        <TableCell
                          colSpan={selectedSlugs.length + 1}
                          className="py-1.5 text-xs font-medium"
                        >
                          {row.category}
                        </TableCell>
                      </TableRow>
                    )}
                    <TableRow className={TABLE_ROW_CLASS}>
                      <TableCell
                        className={cn(
                          "py-1.5 text-muted-foreground",
                          COMPARE_FEATURE_COLUMN_CLASS
                        )}
                      >
                        {row.feature}
                      </TableCell>
                      {selectedSlugs.map((slug) => {
                        const isEditing = editingSlug === slug;
                        const cellValue = isEditing
                          ? (draft[row.field_key] ?? null)
                          : (row.values[slug] ?? null);
                        const initialValue = row.values[slug] ?? null;
                        const isCellDirty =
                          isEditing &&
                          !flightValuesEqual(
                            row.field_key,
                            initialValue,
                            draft[row.field_key] ?? null
                          );

                        return (
                          <TableCell
                            key={slug}
                            className={cn(
                              "py-1.5",
                              COMPARE_AIRLINE_COLUMN_CLASS,
                              diff && !isEditing && "bg-muted/60"
                            )}
                          >
                            <div className="min-w-0 text-left">
                            {row.field_key === "source_url" ? (
                              <ReferenceUrlCell
                                value={row.values[slug] ?? null}
                                diff={diff}
                              />
                            ) : isEditing ? (
                              <FlightCompareValueCell
                                fieldKey={row.field_key}
                                value={cellValue}
                                isEditing
                                isDirty={isCellDirty}
                                diff={diff}
                                onStartEdit={() => startEditing(slug)}
                                onChange={(value) =>
                                  setDraft((prev) => ({
                                    ...prev,
                                    [row.field_key]: value,
                                  }))
                                }
                              />
                            ) : (
                              <FlightCompareValueCell
                                fieldKey={row.field_key}
                                value={cellValue}
                                isEditing={false}
                                isDirty={false}
                                diff={diff}
                                canEdit={canEdit}
                                onStartEdit={() => startEditing(slug)}
                                onChange={() => {}}
                              />
                            )}
                            </div>
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

      <SignInDialog
        open={signInOpen}
        onOpenChange={setSignInOpen}
        password={signInPassword}
        onPasswordChange={setSignInPassword}
        error={signInError}
        signingIn={signingIn}
        onSubmit={handleSignIn}
      />
    </div>
  );
}
