import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import { AlertCircle, CheckCircle2, X } from 'lucide-react';
import { addToast } from '../../lib/uiState';

const SUCCESS_MS = 5000;
const ERROR_MS = 9000;

const ToastContext = createContext(null);

/** Short messages that replace browser alert boxes. */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timers = useRef(new Map());

  const dismiss = useCallback((id) => {
    clearTimeout(timers.current.get(id));
    timers.current.delete(id);
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const show = useCallback((tone, message) => {
    setToasts((current) => {
      const next = addToast(current, tone, message);
      const added = next[next.length - 1];
      timers.current.set(added.id, setTimeout(() => dismiss(added.id), tone === 'error' ? ERROR_MS : SUCCESS_MS));
      return next;
    });
  }, [dismiss]);

  const value = useMemo(() => ({
    success: (message) => show('success', message),
    error: (message) => show('error', message),
  }), [show]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed inset-x-4 bottom-4 z-[60] flex flex-col items-end gap-2 sm:left-auto sm:w-96">
        {toasts.map((toast) => {
          const isError = toast.tone === 'error';
          const Icon = isError ? AlertCircle : CheckCircle2;
          return (
            <div
              key={toast.id}
              role={isError ? 'alert' : 'status'}
              className={`pointer-events-auto flex w-full items-start gap-2 rounded-xl border bg-white p-3 text-sm shadow-lg ${isError ? 'border-rose-300 text-rose-900' : 'border-emerald-300 text-emerald-900'}`}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="flex-1">{toast.message}</span>
              <button type="button" aria-label="Dismiss" onClick={() => dismiss(toast.id)} className="-m-2 flex min-h-11 min-w-11 items-center justify-center rounded-lg text-slate-500 hover:text-slate-800">
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
