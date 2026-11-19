import React, { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import { TextField } from '../components/ui/Field';
import { Badge, Card, PageHeader } from '../components/ui/Page';
import { classLabel, longDate, stateInfo } from '../lib/attendance';
import { useLoad } from '../lib/useLoad';

export default function TeacherAttendanceHistory() {
  const { id } = useParams();
  const [range, setRange] = useState({ start: '', end: '' });
  const info = useLoad((request) => api.getMyClass(id, request), `history-class-${id}`, 'Could not open this class.');
  const history = useLoad(
    (request) => api.getClassHistory(id, { start: range.start || undefined, end: range.end || undefined }, request),
    `history-${id}-${range.start}-${range.end}`,
    'Could not load the attendance history. Please try again.',
  );
  const set = (field) => (event) => setRange((current) => ({ ...current, [field]: event.target.value }));

  const columns = [
    { header: 'Date', mobile: 'title', render: (day) => <Link className="font-semibold text-brand-700 hover:underline" to={`/teacher/classes/${id}/attendance?date=${day.date}`}>{longDate(day.date)}</Link> },
    { header: 'Status', render: (day) => <Badge tone={stateInfo(day.state).tone}>{stateInfo(day.state).label}{day.corrected ? ' · corrected' : ''}</Badge> },
    { header: 'Present', align: 'right', render: (day) => day.present },
    { header: 'Absent', align: 'right', render: (day) => day.absent },
    { header: 'Late', align: 'right', render: (day) => day.late },
    { header: 'Leave', align: 'right', render: (day) => day.leave },
    { header: 'Recorded', align: 'right', render: (day) => `${day.recorded} of ${day.enrolled}` },
  ];

  return (
    <div className="space-y-5">
      <Link to={`/teacher/classes/${id}`} className="inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold text-brand-700 hover:underline">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> {info.data ? classLabel(info.data.grade, info.data.section) : 'Class'}
      </Link>
      <PageHeader title="Attendance History" subtitle="Days with saved attendance. Days nobody recorded are not listed." />
      <Card>
        <div className="grid gap-4 border-b border-slate-200 p-4 sm:grid-cols-2">
          <TextField label="From" type="date" value={range.start} onChange={set('start')} hint="Leave blank for the last 30 days." />
          <TextField label="To" type="date" value={range.end} onChange={set('end')} />
        </div>
        <DataTable
          columns={columns}
          rows={history.data?.days ?? []}
          rowKey={(day) => day.date}
          loading={history.loading}
          error={history.error}
          onRetry={history.reload}
          loadingLabel="Loading history…"
          emptyState={{ title: 'No attendance saved in this period', message: 'Choose Daily Attendance to record a day.' }}
        />
      </Card>
    </div>
  );
}
