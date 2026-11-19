import React from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, CalendarCheck, History } from 'lucide-react';
import { api } from '../api/client';
import { buttonClass } from '../components/ui/Button';
import { Badge, Card, PageHeader } from '../components/ui/Page';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States';
import { classLabel, stateInfo } from '../lib/attendance';
import { useLoad } from '../lib/useLoad';

export default function TeacherClassDetail() {
  const { id } = useParams();
  const { data, loading, error, reload } = useLoad(
    (request) => api.getMyClass(id, request),
    `my-class-${id}`,
    'Could not load this class. Please try again.',
  );

  if (loading) return <LoadingState label="Loading the class…" />;
  if (error) return <ErrorState title="This class could not be opened" message={error} onRetry={reload} />;

  const state = stateInfo(data.today_attendance.state);

  return (
    <div className="space-y-6">
      <Link to="/teacher/classes" className="inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold text-brand-700 hover:underline">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> My Classes
      </Link>
      <PageHeader
        title={classLabel(data.grade, data.section)}
        subtitle={`${data.academic_year} · ${data.enrolled} students`}
        actions={(
          <>
            <Link to={`/teacher/classes/${id}/attendance`} className={buttonClass('primary')}>
              <CalendarCheck className="h-4 w-4" aria-hidden="true" /><span>Daily Attendance</span>
            </Link>
            <Link to={`/teacher/classes/${id}/history`} className={buttonClass('secondary')}>
              <History className="h-4 w-4" aria-hidden="true" /><span>Attendance History</span>
            </Link>
          </>
        )}
      />
      <p className="text-sm text-slate-700">Today: <Badge tone={state.tone}>{state.label}</Badge></p>

      <Card>
        <h2 className="border-b border-slate-200 px-4 py-3 text-base font-bold text-slate-900">Student roster</h2>
        {data.students.length === 0 ? (
          <EmptyState title="No students in this class" message="Students appear here once they are enrolled in this grade and section." />
        ) : (
          <ol className="divide-y divide-slate-100">
            {data.students.map((student, index) => (
              <li key={student.id} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                <span className="w-6 text-right text-xs text-slate-500">{index + 1}</span>
                <span className="min-w-0 flex-1 truncate font-medium text-slate-900">{student.name}</span>
                <span className="text-xs text-slate-600">Roll no. {student.roll_number}</span>
              </li>
            ))}
          </ol>
        )}
      </Card>
    </div>
  );
}
