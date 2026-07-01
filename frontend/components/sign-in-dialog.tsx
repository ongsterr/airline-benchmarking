"use client";

import { type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

type SignInDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  password: string;
  onPasswordChange: (value: string) => void;
  error: string | null;
  signingIn: boolean;
  onSubmit: (e: FormEvent) => void;
  description?: string;
};

export function SignInDialog({
  open,
  onOpenChange,
  password,
  onPasswordChange,
  error,
  signingIn,
  onSubmit,
  description = "Enter the edit password to modify comparison fields and run data updates.",
}: SignInDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogPopup>
        <form onSubmit={onSubmit}>
          <DialogHeader>
            <DialogTitle>Sign in to edit</DialogTitle>
            <DialogDescription>{description}</DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => onPasswordChange(e.target.value)}
              autoComplete="current-password"
              autoFocus
            />
            {error && (
              <p className="mt-2 text-sm text-destructive">{error}</p>
            )}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={signingIn}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={signingIn || !password}>
              {signingIn ? "Signing in…" : "Sign in"}
            </Button>
          </DialogFooter>
        </form>
      </DialogPopup>
    </Dialog>
  );
}
