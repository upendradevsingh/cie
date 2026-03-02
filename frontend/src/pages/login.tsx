import { useState, useEffect, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";
import {
  Eye,
  EyeOff,
  Loader2,
  AlertCircle,
  ArrowRight,
  Building2,
} from "lucide-react";

// ────────────────────────────────────────────────────────────────────
// Login Page
// ────────────────────────────────────────────────────────────────────

type AuthMode = "login" | "register";

export default function LoginPage() {
  const navigate = useNavigate();
  const {
    isAuthenticated,
    login,
    register,
    loginError,
    registerError,
    isLoggingIn,
    isRegistering,
  } = useAuth();

  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFormError(null);

    // Basic validation
    if (!email.trim() || !password.trim()) {
      setFormError("Email and password are required.");
      return;
    }

    if (mode === "register" && (!name.trim() || !orgName.trim())) {
      setFormError("All fields are required.");
      return;
    }

    if (password.length < 8) {
      setFormError("Password must be at least 8 characters.");
      return;
    }

    try {
      if (mode === "login") {
        await login({ email, password });
      } else {
        await register({
          name,
          email,
          password,
          organization_name: orgName,
        });
      }
      navigate("/dashboard", { replace: true });
    } catch {
      // Error is captured by mutation state
    }
  };

  const toggleMode = () => {
    setMode((prev) => (prev === "login" ? "register" : "login"));
    setFormError(null);
  };

  const isSubmitting = isLoggingIn || isRegistering;
  const apiError = mode === "login" ? loginError : registerError;
  const displayError = formError ?? extractErrorMessage(apiError);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-925 px-4">
      {/* Background gradient decoration */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -left-40 -top-40 h-80 w-80 rounded-full bg-primary-600/20 blur-3xl" />
        <div className="absolute -bottom-40 -right-40 h-80 w-80 rounded-full bg-accent-500/15 blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Logo & Tagline */}
        <div className="mb-8 text-center">
          <h1 className="flex items-center justify-center gap-2 text-3xl font-bold text-white">
            <span className="text-accent-500">&#9678;</span>
            SalesLens
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            AI lens into every sales conversation
          </p>
        </div>

        {/* Card */}
        <div className="rounded-xl border border-slate-800 bg-slate-850/80 p-8 shadow-2xl backdrop-blur-sm">
          {/* Header */}
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-white">
              {mode === "login" ? "Welcome back" : "Create your account"}
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              {mode === "login"
                ? "Sign in to your SalesLens workspace"
                : "Set up a new organization on SalesLens"}
            </p>
          </div>

          {/* Error banner */}
          {displayError && (
            <div className="mb-4 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{displayError}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <>
                <InputField
                  label="Full name"
                  type="text"
                  value={name}
                  onChange={setName}
                  placeholder="Jane Doe"
                  autoComplete="name"
                  disabled={isSubmitting}
                />
                <InputField
                  label="Organization name"
                  type="text"
                  value={orgName}
                  onChange={setOrgName}
                  placeholder="Acme Inc."
                  autoComplete="organization"
                  disabled={isSubmitting}
                  icon={<Building2 className="h-4 w-4 text-slate-500" />}
                />
              </>
            )}

            <InputField
              label="Email"
              type="email"
              value={email}
              onChange={setEmail}
              placeholder="you@company.com"
              autoComplete="email"
              disabled={isSubmitting}
            />

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-300">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete={
                    mode === "login" ? "current-password" : "new-password"
                  }
                  disabled={isSubmitting}
                  className={cn(
                    "w-full rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-2.5 pr-10 text-sm text-white",
                    "placeholder:text-slate-500",
                    "focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500/50",
                    "disabled:cursor-not-allowed disabled:opacity-60",
                    "transition-colors duration-150",
                  )}
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowPassword((p) => !p)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className={cn(
                "group flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium",
                "bg-accent-500 text-white hover:bg-accent-600",
                "focus:outline-none focus:ring-2 focus:ring-accent-500/50 focus:ring-offset-2 focus:ring-offset-slate-900",
                "disabled:cursor-not-allowed disabled:opacity-60",
                "transition-all duration-150",
              )}
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  {mode === "login" ? "Sign in" : "Create account"}
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </>
              )}
            </button>
          </form>

          {/* Toggle login/register */}
          <div className="mt-6 text-center text-sm text-slate-400">
            {mode === "login" ? (
              <>
                Don&apos;t have an account?{" "}
                <button
                  type="button"
                  onClick={toggleMode}
                  className="font-medium text-accent-400 hover:text-accent-300 transition-colors"
                >
                  Create new organization
                </button>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={toggleMode}
                  className="font-medium text-accent-400 hover:text-accent-300 transition-colors"
                >
                  Sign in
                </button>
              </>
            )}
          </div>
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-xs text-slate-600">
          By continuing, you agree to SalesLens Terms of Service and Privacy
          Policy.
        </p>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Sub-components
// ────────────────────────────────────────────────────────────────────

interface InputFieldProps {
  label: string;
  type: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  autoComplete?: string;
  disabled?: boolean;
  icon?: React.ReactNode;
}

function InputField({
  label,
  type,
  value,
  onChange,
  placeholder,
  autoComplete,
  disabled,
  icon,
}: InputFieldProps) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-slate-300">
        {label}
      </label>
      <div className="relative">
        {icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2">{icon}</div>
        )}
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          disabled={disabled}
          className={cn(
            "w-full rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-2.5 text-sm text-white",
            "placeholder:text-slate-500",
            "focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500/50",
            "disabled:cursor-not-allowed disabled:opacity-60",
            "transition-colors duration-150",
            icon && "pl-10",
          )}
        />
      </div>
    </div>
  );
}

// ── Helpers ─────────────────────────────────────────────────────────

function extractErrorMessage(error: Error | null): string | null {
  if (!error) return null;
  // Axios wraps the response
  const axiosError = error as unknown as {
    response?: { data?: { detail?: string } };
  };
  if (axiosError.response?.data?.detail) {
    return axiosError.response.data.detail;
  }
  return error.message || "An unexpected error occurred. Please try again.";
}
