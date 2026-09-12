import React from 'react';

export default function StatCard({ title, value, subtitle, icon: Icon, color = 'blue', trend }) {
  const colorMap = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
    red: 'bg-rose-50 text-rose-700 border-rose-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
  };

  const iconBgMap = {
    blue: 'bg-blue-600 text-white',
    green: 'bg-emerald-600 text-white',
    amber: 'bg-amber-500 text-white',
    red: 'bg-rose-600 text-white',
    purple: 'bg-purple-600 text-white',
  };

  return (
    <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</p>
          <h3 className="text-2xl font-bold text-slate-800 mt-1">{value}</h3>
          {subtitle && (
            <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
              {trend && <span className="font-medium text-emerald-600">{trend}</span>}
              <span>{subtitle}</span>
            </p>
          )}
        </div>
        {Icon && (
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center shadow-sm ${iconBgMap[color] || iconBgMap.blue}`}>
            <Icon className="w-6 h-6" />
          </div>
        )}
      </div>
    </div>
  );
}
