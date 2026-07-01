"use client";

import { useCallback, useState, type FormEvent } from "react";
import { AirlineExtractSection } from "@/components/airline-extract-section";
import { AirlineSummaryTable } from "@/components/airline-summary-table";
import { SectionCard } from "@/components/section-card";
import { SignInDialog } from "@/components/sign-in-dialog";
import { getAirlineSummaries, type AirlineSummary } from "@/lib/api";
import { useEditAuth } from "@/lib/use-edit-auth";

type AirlineDashboardProps = {
  initialSummaries: AirlineSummary[];
};

export function AirlineDashboard({ initialSummaries }: AirlineDashboardProps) {
  const [summaries, setSummaries] = useState(initialSummaries);
  const { isAuthenticated, isLoading: authLoading, login } = useEditAuth();
  const [signInOpen, setSignInOpen] = useState(false);
  const [signInPassword, setSignInPassword] = useState("");
  const [signInError, setSignInError] = useState<string | null>(null);
  const [signingIn, setSigningIn] = useState(false);

  const canTrigger = isAuthenticated;

  const refreshSummaries = useCallback(async () => {
    try {
      const next = await getAirlineSummaries();
      setSummaries(next);
    } catch {
      // Keep existing data on refresh failure.
    }
  }, []);

  const openSignIn = useCallback(() => {
    setSignInError(null);
    setSignInOpen(true);
  }, []);

  const handleSignIn = async (e: FormEvent) => {
    e.preventDefault();
    setSignInError(null);
    setSigningIn(true);
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

  return (
    <div className="space-y-6">
      <SectionCard title="Extract Airline">
        <AirlineExtractSection
          canTrigger={canTrigger}
          isAuthLoading={authLoading}
          onSignInRequired={openSignIn}
          onComplete={() => void refreshSummaries()}
        />
      </SectionCard>

      <SectionCard title="Airlines">
        <AirlineSummaryTable summaries={summaries} />
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
