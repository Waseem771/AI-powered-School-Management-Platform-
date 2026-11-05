import React from 'react';

const ICON_TONES = {
  blue: 'bg-brand-50 text-brand-700',
  green: 'bg-emerald-50 text-emerald-700',
  amber: 'bg-amber-50 text-amber-700',
  red: 'bg-rose-50 text-rose-700',
};

export default function StatCard({ title, value, subtitle, icon: Icon, color = 'blue' }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="min-w-0">
        <p className="text-sm font-semibold text-slate-600">{title}</p>
        <p className="mt-1 whitespace-nowrap text-xl font-bold text-navy-900 xl:text-2xl">{value}</p>
        {subtitle && <p className="mt-1 text-xs text-slate-600">{subtitle}</p>}
      </div>
      {Icon && (
        <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${ICON_TONES[color]}`}>
          <Icon className="h-6 w-6" aria-hidden="true" />
        </div>
      )}
    </div>
  );
}
