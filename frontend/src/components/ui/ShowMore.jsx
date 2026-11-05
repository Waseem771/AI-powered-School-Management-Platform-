import React, { useEffect, useState } from 'react';
import { LIST_STEP, nextVisibleCount } from '../../lib/uiState';
import Button from './Button';

/** Shows a long list a step at a time. Starts again whenever the list itself changes. */
export function useShowMore(rows) {
  const [visible, setVisible] = useState(LIST_STEP);
  useEffect(() => setVisible(LIST_STEP), [rows.length]);
  return {
    shown: rows.slice(0, visible),
    hasMore: visible < rows.length,
    showMore: () => setVisible((current) => nextVisibleCount(current, rows.length)),
    total: rows.length,
  };
}

export function ShowMoreButton({ list }) {
  if (!list.hasMore) return null;
  return (
    <div className="flex flex-wrap items-center justify-center gap-3 border-t border-slate-200 p-3">
      <span className="text-sm text-slate-600">Showing {list.shown.length} of {list.total}</span>
      <Button variant="secondary" onClick={list.showMore}>Show more</Button>
    </div>
  );
}
