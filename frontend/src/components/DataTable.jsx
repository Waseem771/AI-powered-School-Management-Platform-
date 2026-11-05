import React from 'react';
import { EmptyState, ErrorState, LoadingState } from './ui/States';
import { viewState } from '../lib/uiState';
import { ShowMoreButton, useShowMore } from './ui/ShowMore';

const alignClass = (column) => (column.align === 'right' ? 'text-right' : 'text-left');

function Cards({ columns, rows, rowKey }) {
  const titleColumn = columns.find((column) => column.mobile === 'title');
  const details = columns.filter((column) => !column.mobile);
  const actions = columns.find((column) => column.mobile === 'actions');

  return (
    <ul className="divide-y divide-slate-200 md:hidden">
      {rows.map((row) => (
        <li key={rowKey(row)} className="space-y-2 p-4">
          {titleColumn && <div className="text-sm">{titleColumn.render(row)}</div>}
          <dl className="space-y-1.5 text-sm">
            {details.map((column) => (
              <div key={column.header} className="flex items-baseline justify-between gap-4">
                <dt className="shrink-0 text-xs font-semibold text-slate-600">{column.header}</dt>
                <dd className="min-w-0 text-right text-slate-800">{column.render(row)}</dd>
              </div>
            ))}
          </dl>
          {actions && <div className="flex flex-wrap items-center gap-2 pt-1">{actions.render(row)}</div>}
        </li>
      ))}
    </ul>
  );
}

function Table({ columns, rows, rowKey }) {
  return (
    <div className="hidden overflow-x-auto md:block">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-xs font-semibold text-slate-600">
            {columns.map((column) => (
              <th key={column.header} scope="col" className={`px-4 py-3 ${alignClass(column)}`}>{column.header}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 text-sm text-slate-800">
          {rows.map((row) => (
            <tr key={rowKey(row)} className="hover:bg-slate-50">
              {columns.map((column) => (
                <td key={column.header} className={`px-4 py-2.5 ${alignClass(column)}`}>{column.render(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * A table on larger screens and cards on phones, with one way of showing loading, failed, and empty.
 *
 * Each column has `header` and `render(row)`, plus optional `align: 'right'` and `mobile`:
 * 'title' for the card's heading and 'actions' for its buttons. Any other column is a labelled line.
 */
export default function DataTable({ columns, rows, rowKey = (row) => row.id, loading, error, onRetry, loadingLabel, emptyState }) {
  const list = useShowMore(rows);
  const state = viewState({ loading, error, count: rows.length });
  if (state === 'loading') return <LoadingState label={loadingLabel} />;
  if (state === 'error') return <ErrorState message={error} onRetry={onRetry} />;
  if (state === 'empty') return <EmptyState {...emptyState} />;
  return (
    <>
      <Cards columns={columns} rows={list.shown} rowKey={rowKey} />
      <Table columns={columns} rows={list.shown} rowKey={rowKey} />
      <ShowMoreButton list={list} />
    </>
  );
}
