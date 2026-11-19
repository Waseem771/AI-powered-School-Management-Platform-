import React from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, ChevronRight } from 'lucide-react';
import { api } from '../api/client';
import { Badge, PageHeader } from '../components/ui/Page';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States';
import { classLabel, longDate, stateInfo } from '../lib/attendance';
import { useLoad } from '../lib/useLoad';

export default function TeacherClasses() {
  const { data, loading, error, reload } = useLoad(
    (request) => api.getMyClasses(request),
    'my-classes',
    'Could not load your classes. Please try again.',
  );

  if (loading) return <LoadingState label="Loading your classes…" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  return (
    <div className="space-y-6">
      <PageHeader title="My Classes" subtitle={`Today is ${longDate(data.today)}.`} />
      {data.classes.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white">
          <EmptyState
            icon={BookOpen}
            title="No classes assigned yet"
            message="The school office assigns classes to teachers. Ask them to assign yours, then check again."
          />
        </div>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {data.classes.map((item) => {
            const state = stateInfo(item.today_attendance.state);
            return (
              <li key={item.id}>
                <Link
                  to={`/teacher/classes/${item.id}`}
                  className="flex min-h-11 flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-colors hover:border-brand-300 hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-lg font-bold text-navy-900">{item.grade}</p>
                      <p className="text-sm text-slate-600">Section {item.section}</p>
                    </div>
                    <ChevronRight className="mt-1 h-5 w-5 shrink-0 text-slate-400" aria-hidden="true" />
                  </div>
                  <dl className="space-y-1 text-sm">
                    <div className="flex justify-between gap-3"><dt className="text-slate-600">Session</dt><dd className="text-slate-900">{item.academic_year}{item.is_current_session ? '' : ' (closed)'}</dd></div>
                    <div className="flex justify-between gap-3"><dt className="text-slate-600">Students</dt><dd className="font-semibold text-slate-900">{item.enrolled}</dd></div>
                    <div className="flex items-center justify-between gap-3">
                      <dt className="text-slate-600">Today's attendance</dt>
                      <dd><Badge tone={state.tone}>{state.label}{item.today_attendance.state === 'partial' ? ` (${item.today_attendance.recorded} of ${item.enrolled})` : ''}</Badge></dd>
                    </div>
                  </dl>
                  <span className="sr-only">Open {classLabel(item.grade, item.section)}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
