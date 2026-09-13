import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
          <section className="max-w-md w-full rounded-2xl border border-slate-200 bg-white p-7 text-center shadow-xl shadow-slate-900/5" aria-labelledby="app-error-title">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
              <AlertTriangle className="h-6 w-6" aria-hidden="true" />
            </div>
            <h1 id="app-error-title" className="text-lg font-bold text-slate-900">Something needs a refresh</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">The portal could not finish loading. Your data has not been changed.</p>
            <button onClick={() => window.location.reload()} className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2">
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Refresh portal
            </button>
          </section>
        </div>
      );
    }

    return this.props.children;
  }
}
