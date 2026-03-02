import { create } from "zustand";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useCallback } from "react";
import type { User, UserRole, LoginRequest, RegisterRequest, AuthResponse } from "@/lib/types";
import * as api from "@/lib/api";

// ── Zustand store for token state ──────────────────────────────────

interface AuthStore {
  accessToken: string | null;
  setTokens: (access: string, refresh: string) => void;
  clearTokens: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  accessToken: localStorage.getItem("access_token"),
  setTokens: (access, refresh) => {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
    set({ accessToken: access });
  },
  clearTokens: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    set({ accessToken: null });
  },
}));

// ── Main auth hook ─────────────────────────────────────────────────

export function useAuth() {
  const queryClient = useQueryClient();
  const { accessToken, setTokens, clearTokens } = useAuthStore();

  const {
    data: user,
    isLoading,
    error,
  } = useQuery<User>({
    queryKey: ["auth", "me"],
    queryFn: api.getMe,
    enabled: !!accessToken,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const loginMutation = useMutation<AuthResponse, Error, LoginRequest>({
    mutationFn: api.login,
    onSuccess: (data) => {
      setTokens(data.tokens.access_token, data.tokens.refresh_token);
      queryClient.setQueryData(["auth", "me"], data.user);
    },
  });

  const registerMutation = useMutation<AuthResponse, Error, RegisterRequest>({
    mutationFn: api.register,
    onSuccess: (data) => {
      setTokens(data.tokens.access_token, data.tokens.refresh_token);
      queryClient.setQueryData(["auth", "me"], data.user);
    },
  });

  const logout = useCallback(() => {
    clearTokens();
    queryClient.clear();
  }, [clearTokens, queryClient]);

  return {
    user: user ?? null,
    isLoading,
    isAuthenticated: !!accessToken && !!user,
    error,
    login: loginMutation.mutateAsync,
    loginError: loginMutation.error,
    isLoggingIn: loginMutation.isPending,
    register: registerMutation.mutateAsync,
    registerError: registerMutation.error,
    isRegistering: registerMutation.isPending,
    logout,
  };
}

// ── Helper hook for checking roles ─────────────────────────────────

export function useRequireRole(requiredRoles: UserRole[]) {
  const { user } = useAuth();
  return user ? requiredRoles.includes(user.role) : false;
}

// ── Redirect-aware login ───────────────────────────────────────────

export function useLoginRedirect() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const redirectAfterLogin = useCallback(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  return { redirectAfterLogin };
}
