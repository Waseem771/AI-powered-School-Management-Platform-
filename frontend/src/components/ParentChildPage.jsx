import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { FilterChips, PageHeader } from './ui/Page';
import { EmptyState, ErrorState, LoadingState } from './ui/States';
import { classText, pickChild } from '../lib/parent';
import { useLoad } from '../lib/useLoad';

/**
 * The frame of every per-child parent screen: a title, a way to switch between children when there is
 * more than one, and the screen itself for the chosen child. The child is kept in the address
 * (?child=4), so links from the dashboard open the right one. The server decides which children exist.
 */
export default function ParentChildPage({ title, subtitle, children: renderChild }) {
  const [params, setParams] = useSearchParams();
  const { data, loading, error, reload } = useLoad(
    (options) => api.getParentChildren(options),
    'parent-children',
    'Could not load your children. Please try again.',
  );

  if (loading) return <LoadingState label="Loading…" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const children = data.children;
  const child = pickChild(children, params.get('child'));
  if (!child) {
    return (
      <div className="space-y-6">
        <PageHeader title={title} />
        <EmptyState
          title="No children are linked to your account yet"
          message="Please contact the school office, and they will link your child to this account."
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={title}
        subtitle={subtitle}
      />
      {children.length > 1 ? (
        <FilterChips
          label="Choose a child"
          value={child.id}
          onChange={(id) => setParams({ child: String(id) }, { replace: true })}
          options={children.map((option) => ({ value: option.id, label: option.name }))}
        />
      ) : null}
      <p className="text-sm text-slate-700">
        <span className="font-bold text-slate-900">{child.name}</span> &bull; {classText(child)} &bull; Roll #{child.roll_number}
        {!child.enrolled && <span className="ml-2 font-semibold text-amber-800">(no longer enrolled)</span>}
      </p>
      {renderChild(child)}
    </div>
  );
}
