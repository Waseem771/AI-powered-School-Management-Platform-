import React, { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import ParentChildPage from '../components/ParentChildPage';
import StatCard from '../components/StatCard';
import Button from '../components/ui/Button';
import { Badge, Card } from '../components/ui/Page';
import { ErrorState, LoadingState } from '../components/ui/States';
import { longDate, statusLabel, statusTone } from '../lib/attendance';
import { canGoForward, monthTitle, rateTone, shiftMonth } from '../lib/parent';
import { useLoad } from '../lib/useLoad';

const COUNT_LABELS = [['present', 'Present'], ['late', 'Late'], ['absent', 'Absent'], ['leave', 'Leave']];

function Counts({ summary }) {
  return (
    <ul className="flex flex-wrap gap-2" aria-label="Days by status">
      {COUNT_LABELS.map(([key, label]) => (
        <li key={key}><Badge tone={statusTone(key)}>{label}: {summary[key]}</Badge></li>
      ))}
    </ul>
  );
}

const columns = [
  { header: 'Date', mobile: 'title', render: (day) => <span className="font-semibold text-slate-900">{longDate(day.date)}</span> },
  { header: 'Status', render: (day) => <Badge tone={statusTone(day.status)}>{statusLabel(day.status)}</Badge> },
];

function AttendanceBody({ child }) {
  const [month, setMonth] = useState(null); // null means this month, as the school sees it
  const { data, loading, error, reload } = useLoad(
    (options) => api.getParentChildAttendance(child.id, month ? { month } : {}, options),
    `${child.id}|${month}`,
    'Could not load the attendance. Please try again.',
  );

  if (error && !data) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <LoadingState label="Loading attendance…" />;

  const monthly = data.month_summary;
  const wholeSession = data.session_summary;

  return (
    <>
      <section aria-label="Attendance summary" className="grid gap-4 sm:grid-cols-2">
        <StatCard
          title={monthTitle(data.month)}
          value={monthly.attendance_rate === null ? 'No records' : `${monthly.attendance_rate}%`}
          subtitle={`${monthly.recorded} ${monthly.recorded === 1 ? 'day' : 'days'} recorded`}
        />
        <StatCard
          title={data.session_label ? `Session ${data.session_label}` : 'This session'}
          value={wholeSession.attendance_rate === null ? 'No records' : `${wholeSession.attendance_rate}%`}
          subtitle={`${wholeSession.recorded} ${wholeSession.recorded === 1 ? 'day' : 'days'} recorded`}
          color={rateTone(wholeSession.attendance_rate) === 'bad' ? 'red' : 'blue'}
        />
      </section>
      <p className="text-xs text-slate-600">
        The percentage counts days when your child was present or late, out of the days the teacher recorded. A day with no record is not counted.
      </p>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-4">
          <div className="flex items-center gap-2">
            <Button variant="secondary" aria-label="Previous month" disabled={loading} onClick={() => setMonth(shiftMonth(data.month, -1))}>
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            </Button>
            <h2 className="min-w-36 text-center text-base font-bold text-slate-900" aria-live="polite">{monthTitle(data.month)}</h2>
            <Button
              variant="secondary"
              aria-label="Next month"
              disabled={loading || !canGoForward(data.month, data.today)}
              onClick={() => setMonth(shiftMonth(data.month, 1))}
            >
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
          <Counts summary={monthly} />
        </div>
        <DataTable
          columns={columns}
          rows={data.days}
          rowKey={(day) => day.date}
          loading={loading}
          error={error}
          onRetry={reload}
          loadingLabel="Loading attendance…"
          emptyState={{
            title: 'No attendance recorded this month',
            message: `No attendance has been recorded for ${monthTitle(data.month)}. A day with no record is never counted as absent.`,
          }}
        />
      </Card>
    </>
  );
}

export default function ParentAttendance() {
  return (
    <ParentChildPage title="Attendance" subtitle="Daily and monthly attendance, as recorded by the teachers.">
      {(child) => <AttendanceBody key={child.id} child={child} />}
    </ParentChildPage>
  );
}
