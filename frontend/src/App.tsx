import { BrowserRouter, Routes, Route, Navigate, Outlet, NavLink, Link } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import {
  LayoutDashboard,
  Phone,
  BarChart3,
  Trophy,
  Settings,
  FileText,
  LogOut,
  Menu,
  X,
  ChevronDown,
} from "lucide-react";
import { useAuth, useAuthStore } from "@/hooks/use-auth";
import { useToast, type Toast as ToastType } from "@/hooks/use-toast";
import { cn, getInitials } from "@/lib/utils";

// ── Page imports ────────────────────────────────────────────────────

import LoginPage from "@/pages/login";
import DashboardPage from "@/pages/dashboard";
import CallsListPage from "@/pages/calls-list";
import CallDetailPage from "@/pages/call-detail";
import AnalyticsPage from "@/pages/analytics";
import LeaderboardPage from "@/pages/leaderboard";
import SettingsPage from "@/pages/settings";
import ReportsPage from "@/pages/reports";

// ── Query Client ────────────────────────────────────────────────────

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60 * 1000, // 2 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// ── Navigation Items ────────────────────────────────────────────────

interface NavItem {
  label: string;
  path: string;
  icon: ReactNode;
}

const navItems: NavItem[] = [
  { label: "Dashboard", path: "/dashboard", icon: <LayoutDashboard size={20} /> },
  { label: "Calls", path: "/calls", icon: <Phone size={20} /> },
  { label: "Analytics", path: "/analytics", icon: <BarChart3 size={20} /> },
  { label: "Leaderboard", path: "/leaderboard", icon: <Trophy size={20} /> },
  { label: "Reports", path: "/reports", icon: <FileText size={20} /> },
  { label: "Settings", path: "/settings", icon: <Settings size={20} /> },
];

// ── Protected Route Wrapper ─────────────────────────────────────────

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const { accessToken } = useAuthStore();

  if (isLoading && accessToken) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated && !accessToken) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

// ── Toast Renderer ──────────────────────────────────────────────────

function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t: ToastType) => (
        <div
          key={t.id}
          className={cn(
            "animate-slide-in-right rounded-lg border px-4 py-3 shadow-lg",
            "max-w-sm",
            t.variant === "success" && "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
            t.variant === "error" && "border-red-500/30 bg-red-500/10 text-red-400",
            t.variant === "warning" && "border-amber-500/30 bg-amber-500/10 text-amber-400",
            t.variant === "default" && "border-border bg-card text-foreground",
          )}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-medium">{t.title}</p>
              {t.description && (
                <p className="mt-1 text-xs opacity-80">{t.description}</p>
              )}
            </div>
            <button
              onClick={() => removeToast(t.id)}
              className="shrink-0 opacity-60 hover:opacity-100"
            >
              <X size={14} />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Sidebar Layout ──────────────────────────────────────────────────

function AppLayout() {
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-background">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-card transition-transform duration-200 lg:static lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 border-b border-border px-6">
          <Link to="/dashboard" className="flex items-center gap-2">
            <span className="text-xl text-accent">&#9678;</span>
            <span className="text-lg font-bold text-foreground">SalesLens</span>
          </Link>
          <button
            className="ml-auto lg:hidden"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={20} className="text-muted-foreground" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-accent/10 text-accent"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )
              }
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t border-border p-3">
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors hover:bg-muted"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                {user ? getInitials(user.full_name) : "?"}
              </div>
              <div className="flex-1 text-left">
                <p className="text-sm font-medium text-foreground">
                  {user?.full_name ?? "Loading..."}
                </p>
                <p className="text-xs text-muted-foreground">{user?.role ?? ""}</p>
              </div>
              <ChevronDown
                size={16}
                className={cn(
                  "text-muted-foreground transition-transform",
                  userMenuOpen && "rotate-180",
                )}
              />
            </button>

            {/* Dropdown menu */}
            {userMenuOpen && (
              <div className="absolute bottom-full left-0 mb-1 w-full rounded-md border border-border bg-popover py-1 shadow-lg">
                <button
                  onClick={() => {
                    setUserMenuOpen(false);
                    logout();
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                >
                  <LogOut size={16} />
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col">
        {/* Top bar (mobile) */}
        <header className="flex h-16 items-center gap-4 border-b border-border bg-card px-4 lg:hidden">
          <button onClick={() => setSidebarOpen(true)}>
            <Menu size={20} className="text-muted-foreground" />
          </button>
          <div className="flex items-center gap-2">
            <span className="text-lg text-accent">&#9678;</span>
            <span className="text-base font-bold text-foreground">SalesLens</span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

// ── App Router (rendered inside providers) ──────────────────────────

function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected routes with sidebar layout */}
        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/calls" element={<CallsListPage />} />
          <Route path="/calls/:id" element={<CallDetailPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/leaderboard" element={<LeaderboardPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/reports" element={<ReportsPage />} />
        </Route>

        {/* Catch-all redirect */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>

      {/* Toast notifications */}
      <ToastContainer />
    </BrowserRouter>
  );
}

// ── App Component (top-level, wraps providers) ──────────────────────

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppRouter />
    </QueryClientProvider>
  );
}
