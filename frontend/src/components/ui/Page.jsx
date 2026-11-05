import React from 'react';

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-navy-900">{title}</h1>
        {subtitle && <p className="mt-0.5 text-sm text-slate-600">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ className = '', children }) {
  return <div className={`rounded-2xl border border-slate-200 bg-white shadow-sm ${className}`}>{children}</div>;
}

/** A row of choices where one is on. Scrolls sideways on a phone rather than wrapping out of sight. */
export function FilterChips({ label, options, value, onChange }) {
  return (
    <div role="group" aria-label={label} className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={value === option.value}
          onClick={() => onChange(option.value)}
          className={`min-h-11 whitespace-nowrap rounded-xl px-3.5 text-sm font-semibold transition-colors ${
            value === option.value ? 'bg-navy-800 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

const BADGE_TONES = {
  neutral: 'border-slate-200 bg-slate-100 text-slate-800',
  good: 'border-emerald-200 bg-emerald-100 text-emerald-900',
  warn: 'border-amber-200 bg-amber-100 text-amber-900',
  bad: 'border-rose-200 bg-rose-100 text-rose-900',
  info: 'border-brand-200 bg-brand-50 text-brand-800',
};

export function Badge({ tone = 'neutral', children }) {
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold ${BADGE_TONES[tone]}`}>
      {children}
    </span>
  );
}
