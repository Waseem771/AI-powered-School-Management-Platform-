import React from 'react';

export default function DataTable({ columns, data, loading, emptyMessage = "No records found." }) {
  if (loading) {
    return (
      <div className="text-center py-12 text-slate-400 text-xs">
        Loading records...
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-12 text-slate-400 text-xs">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-slate-50/75 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
            {columns.map((col, idx) => (
              <th
                key={idx}
                className={`py-3.5 px-4 ${col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
          {data.map((row, rowIdx) => (
            <tr key={rowIdx} className="hover:bg-slate-50/80 transition-colors">
              {columns.map((col, colIdx) => (
                <td
                  key={colIdx}
                  className={`py-3.5 px-4 ${col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'}`}
                >
                  {col.render ? col.render(row) : row[col.accessor]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
