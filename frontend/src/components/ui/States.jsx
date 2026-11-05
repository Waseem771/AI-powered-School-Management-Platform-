import React from 'react';
import { AlertCircle, Inbox, Loader2, RefreshCw } from 'lucide-react';
import Button from './Button';

export function LoadingState({ label = 'Loading…' }) {
  return (
    <div role="status" className="flex flex-col items-center gap-3 px-4 py-14 text-center">
      <Loader2 className="h-7 w-7 animate-spin text-brand-600" aria-hidden="true" />
      <p className="text-sm font-medium text-slate-600">{label}</p>
    </div>
  );
}

export function EmptyState({ icon: Icon = Inbox, title, message, action }) {
  return (
    <div className="flex flex-col items-center gap-2 px-4 py-14 text-center">
      <Icon className="h-8 w-8 text-slate-400" aria-hidden="true" />
      <p className="text-sm font-bold text-slate-800">{title}</p>
      {message && <p className="max-w-md text-sm text-slate-600">{message}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function ErrorState({ title = 'This could not be loaded', message, onRetry }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-2 px-4 py-14 text-center">
      <AlertCircle className="h-8 w-8 text-rose-700" aria-hidden="true" />
      <p className="text-sm font-bold text-slate-800">{title}</p>
      {message && <p className="max-w-md text-sm text-slate-600">{message}</p>}
      {onRetry && (
        <Button variant="secondary" onClick={onRetry} className="mt-2">
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          <span>Try again</span>
        </Button>
      )}
    </div>
  );
}

/** A problem inside a form or dialog, where the rest of the content should stay in place. */
export function ErrorNotice({ children }) {
  if (!children) return null;
  return (
    <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <span>{children}</span>
    </div>
  );
}
