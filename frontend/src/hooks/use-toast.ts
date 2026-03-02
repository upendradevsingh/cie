import { create } from "zustand";

export type ToastVariant = "default" | "success" | "error" | "warning";

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
  duration: number;
}

interface ToastState {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
  clearToasts: () => void;
}

let toastCounter = 0;

const useToastStore = create<ToastState>((set) => ({
  toasts: [],

  addToast: (toast) => {
    const id = `toast-${++toastCounter}-${Date.now()}`;
    const newToast: Toast = { ...toast, id };

    set((state) => ({
      toasts: [...state.toasts, newToast],
    }));

    // Auto-remove after duration
    if (toast.duration > 0) {
      setTimeout(() => {
        set((state) => ({
          toasts: state.toasts.filter((t) => t.id !== id),
        }));
      }, toast.duration);
    }
  },

  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },

  clearToasts: () => {
    set({ toasts: [] });
  },
}));

/**
 * Hook for managing toast notifications.
 * Returns helpers to show various types of toasts and access active toasts.
 */
export function useToast() {
  const { toasts, addToast, removeToast, clearToasts } = useToastStore();

  function toast(options: {
    title: string;
    description?: string;
    variant?: ToastVariant;
    duration?: number;
  }) {
    addToast({
      title: options.title,
      description: options.description,
      variant: options.variant ?? "default",
      duration: options.duration ?? 5000,
    });
  }

  function success(title: string, description?: string) {
    addToast({
      title,
      description,
      variant: "success",
      duration: 5000,
    });
  }

  function error(title: string, description?: string) {
    addToast({
      title,
      description,
      variant: "error",
      duration: 7000,
    });
  }

  function warning(title: string, description?: string) {
    addToast({
      title,
      description,
      variant: "warning",
      duration: 6000,
    });
  }

  return {
    toasts,
    toast,
    success,
    error,
    warning,
    removeToast,
    clearToasts,
  };
}
