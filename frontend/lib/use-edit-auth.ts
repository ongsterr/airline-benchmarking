"use client";

import { useCallback, useEffect, useState } from "react";
import {
  clearEditAuthToken,
  getEditAuthStatus,
  getEditAuthToken,
  loginForEdit,
  logoutForEdit,
} from "@/lib/api";

export function useEditAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    const token = getEditAuthToken();
    if (!token) {
      setIsAuthenticated(false);
      return;
    }
    const authenticated = await getEditAuthStatus();
    if (!authenticated) {
      clearEditAuthToken();
    }
    setIsAuthenticated(authenticated);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setIsLoading(true);
      try {
        const authenticated = await getEditAuthStatus();
        if (!cancelled) {
          if (!authenticated && getEditAuthToken()) {
            clearEditAuthToken();
          }
          setIsAuthenticated(authenticated);
        }
      } catch {
        if (!cancelled) {
          setIsAuthenticated(false);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(
    async (password: string) => {
      await loginForEdit(password);
      await refresh();
      setIsAuthenticated(true);
    },
    [refresh]
  );

  const logout = useCallback(async () => {
    await logoutForEdit();
    setIsAuthenticated(false);
  }, []);

  return {
    isAuthenticated,
    isLoading,
    login,
    logout,
  };
}
