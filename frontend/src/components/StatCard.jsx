import React from 'react';

const ICON_TONES = {
  blue: 'bg-brand-50 text-brand-700',
  green: 'bg-emerald-50 text-emerald-700',
  amber: 'bg-amber-50 text-amber-700',
  red: 'bg-rose-50 text-rose-700',
};

/** The icon sits beside the title, so a large figure always has the card's full width. */
export default function StatCard({ title, value, subtitle, icon: Icon, color = 'blue' }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <p className="min-w-0 text-sm font-semibold text-slate-600">{title}</p>
        {Icon && (
          <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${ICON_TONES[color]}`}>
            <Icon className="h-5 w-5" aria-hidden="true" />
          </div>
        )}
      </div>
      <p className="mt-1 break-words text-2xl font-bold text-navy-900">{value}</p>
      {subtitle && <p className="mt-1 text-xs text-slate-600">{subtitle}</p>}
    </div>
  );
}
