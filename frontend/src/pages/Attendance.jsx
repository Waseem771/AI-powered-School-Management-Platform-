import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Download, Printer } from 'lucide-react';
import { api } from '../api/client';
import { ClassDayDialog, StudentHistoryDialog } from '../components/AttendanceDialogs';
import DataTable from '../components/DataTable';
import Button, { buttonClass } from '../components/ui/Button';
import { SelectField, TextField } from '../components/ui/Field';
import { Badge, Card, FilterChips, PageHeader } from '../components/ui/Page';
import { ErrorState, LoadingState } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import { classLabel, longDate, monthOf, monthRange, rateText, schoolToday, shiftDate, stateInfo } from '../lib/attendance';
import { saveBlob } from '../lib/download';
import { apiErrorMessage } from '../lib/errors';
import { useLoad } from '../lib/useLoad';

const TABS = [
  { value: 'daily', label: 'Daily' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'absentees', label: 'Frequent absences' },
  { value: 'changes', label: 'Corrections log' },
];

function Totals({ items }) {
  return (
    <dl className="grid grid-cols-2 gap-3 border-b border-slate-200 p-4 sm:grid-cols-3 lg:grid-cols-6">
      {items.map(([label, value]) => (
        <div key={label}><dt className="text-xs font-semibold text-slate-600">{label}</dt><dd className="text-xl font-bold text-navy-900">{value}</dd></div>
      ))}
    </dl>
  );
}

function DailyTab({ filters, date, onOpen }) {
  const { data, loading, error, reload } = useLoad(
    (request) => api.getAttendanceOverview({ date, ...filters }, request),
    `overview-${date}-${JSON.stringify(filters)}`,
    'Could not load attendance for this day.',
  );
  const columns = [
    { header: 'Class', mobile: 'title', render: (row) => <span className="font-semibold text-slate-900">{classLabel(row.grade, row.section)}</span> },
    { header: 'Teachers', render: (row) => (row.teachers.length ? row.teachers.join(', ') : 'None assigned') },
    { header: 'Status', render: (row) => <Badge tone={stateInfo(row.state).tone}>{stateInfo(row.state).label}</Badge> },
    { header: 'Present', align: 'right', render: (row) => row.present },
    { header: 'Absent', align: 'right', render: (row) => row.absent },
    { header: 'Late', align: 'right', render: (row) => row.late },
    { header: 'Leave', align: 'right', render: (row) => row.leave },
    { header: 'Not recorded', align: 'right', render: (row) => row.not_recorded },
    {
      header: 'Open', mobile: 'actions', align: 'right',
      render: (row) => (
        <Button variant="secondary" onClick={() => onOpen(row)}>
          {row.state === 'not_submitted' ? 'Record' : 'View / correct'}<span className="sr-only"> {classLabel(row.grade, row.section)}</span>
        </Button>
      ),
    },
  ];
  return (
    <Card>
      {data && (
        <Totals items={[
          ['Students', data.totals.enrolled], ['Recorded', data.totals.recorded], ['Not recorded', data.totals.not_recorded],
          ['Absent', data.totals.absent], ['Late', data.totals.late], ['Classes not submitted', data.classes_not_submitted],
        ]}
        />
      )}
      <DataTable columns={columns} rows={data?.classes ?? []} rowKey={(row) => classLabel(row.grade, row.section)}
        loading={loading} error={error} onRetry={reload} loadingLabel="Loading classes…"
        emptyState={{ title: 'No classes match', message: 'Change the grade or section filter.' }} />
    </Card>
  );
}

function MonthlyTab({ filters, month }) {
  const { data, loading, error, reload } = useLoad(
    (request) => api.getAttendanceMonthly({ month, ...filters }, request),
    `monthly-${month}-${JSON.stringify(filters)}`,
    'Could not load the monthly summary.',
  );
  const columns = [
    { header: 'Class', mobile: 'title', render: (row) => <span className="font-semibold text-slate-900">{classLabel(row.grade, row.section)}</span> },
    { header: 'Days recorded', align: 'right', render: (row) => row.days_recorded },
    { header: 'Present', align: 'right', render: (row) => row.present },
    { header: 'Absent', align: 'right', render: (row) => row.absent },
    { header: 'Late', align: 'right', render: (row) => row.late },
    { header: 'Leave', align: 'right', render: (row) => row.leave },
    { header: 'Attendance', align: 'right', render: (row) => rateText(row.attendance_rate) },
  ];
  return (
    <Card>
      {data && <Totals items={[['Records', data.totals.recorded], ['Present', data.totals.present], ['Absent', data.totals.absent], ['Late', data.totals.late], ['Leave', data.totals.leave], ['Attendance', rateText(data.totals.attendance_rate)]]} />}
      <DataTable columns={columns} rows={data?.classes ?? []} rowKey={(row) => classLabel(row.grade, row.section)}
        loading={loading} error={error} onRetry={reload} loadingLabel="Loading summary…" emptyState={{ title: 'No classes match' }} />
      <p className="border-t border-slate-200 p-3 text-xs text-slate-600">Attendance counts Present and Late as attended. It uses recorded days only; a day nobody recorded is not counted.</p>
    </Card>
  );
}

function AbsenteesTab({ filters, range, minAbsences, onStudent }) {
  const { data, loading, error, reload } = useLoad(
    (request) => api.getFrequentAbsentees({ ...range, min_absences: minAbsences, ...filters }, request),
    `absentees-${range.start}-${range.end}-${minAbsences}-${JSON.stringify(filters)}`,
    'Could not load the list.',
  );
  const columns = [
    { header: 'Student', mobile: 'title', render: (s) => <div><p className="font-semibold text-slate-900">{s.name}</p><p className="text-xs text-slate-600">Roll no. {s.roll_number}</p></div> },
    { header: 'Class', render: (s) => classLabel(s.grade, s.section) },
    { header: 'Absences', align: 'right', render: (s) => s.absent },
    { header: 'Days recorded', align: 'right', render: (s) => s.days_recorded },
    { header: 'Absence rate', align: 'right', render: (s) => `${s.absence_rate}%` },
    { header: 'History', mobile: 'actions', align: 'right', render: (s) => <Button variant="secondary" onClick={() => onStudent(s)}>View history<span className="sr-only"> of {s.name}</span></Button> },
  ];
  return (
    <Card>
      <DataTable columns={columns} rows={data?.students ?? []} loading={loading} error={error} onRetry={reload} loadingLabel="Loading…"
        emptyState={{ title: 'Nobody has this many recorded absences', message: 'Lower the minimum, or widen the dates.' }} />
    </Card>
  );
}

function ChangesTab({ filters, range }) {
  const { data, loading, error, reload } = useLoad(
    (request) => api.getAttendanceChanges({ ...range, ...filters }, request),
    `changes-${range.start}-${range.end}-${JSON.stringify(filters)}`,
    'Could not load the corrections.',
  );
  const columns = [
    { header: 'Student', mobile: 'title', render: (c) => <div><p className="font-semibold text-slate-900">{c.student}</p><p className="text-xs text-slate-600">{classLabel(c.grade, c.section)} · {longDate(c.date)}</p></div> },
    { header: 'Change', render: (c) => `${c.old_status} to ${c.new_status}` },
    { header: 'Reason', render: (c) => c.reason },
    { header: 'By', render: (c) => c.changed_by },
  ];
  return (
    <Card>
      <DataTable columns={columns} rows={data?.changes ?? []} rowKey={(c) => `${c.date}-${c.roll_number}-${c.changed_at}`}
        loading={loading} error={error} onRetry={reload} loadingLabel="Loading…" emptyState={{ title: 'No corrections in this period' }} />
    </Card>
  );
}

export default function Attendance() {
  const toast = useToast();
  const today = schoolToday();
  const [tab, setTab] = useState('daily');
  const [grade, setGrade] = useState('');
  const [section, setSection] = useState('');
  const [yearId, setYearId] = useState('');
  const [date, setDate] = useState(today);
  const [month, setMonth] = useState(monthOf(today));
  const [range, setRange] = useState({ start: shiftDate(today, -29), end: today });
  const [minAbsences, setMinAbsences] = useState(3);
  const [openClass, setOpenClass] = useState(null);
  const [openStudent, setOpenStudent] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [version, setVersion] = useState(0);

  const options = useLoad((request) => api.getAssignmentOptions(request), 'attendance-options', 'Could not load the class list.');
  if (options.loading) return <LoadingState label="Loading…" />;
  if (options.error) return <ErrorState message={options.error} onRetry={options.reload} />;

  const filters = { grade: grade || undefined, section: section || undefined, academic_year_id: yearId || undefined };
  const activeRange = tab === 'daily' ? { start: date, end: date } : tab === 'monthly' ? monthRange(month) : range;

  const exportCsv = async () => {
    setExporting(true);
    try {
      const { start, end } = activeRange;
      const blob = await api.getAttendanceCsv({ start, end, ...filters });
      saveBlob(blob, `attendance-${start}-to-${end}.csv`);
      toast.success('Attendance file downloaded.');
    } catch (error) {
      const message = error?.response?.data instanceof Blob ? await error.response.data.text().then((t) => { try { return JSON.parse(t).detail; } catch { return ''; } }) : '';
      toast.error(typeof message === 'string' && message ? message : apiErrorMessage(error, 'Could not download the file.'));
    } finally {
      setExporting(false);
    }
  };

  const reportQuery = new URLSearchParams({ ...activeRange, ...(grade && { grade }), ...(section && { section }) });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Attendance"
        subtitle="What teachers have recorded. A class nobody has submitted is shown as not submitted, never as absent."
        actions={(
          <>
            <Button variant="secondary" onClick={exportCsv} disabled={exporting} aria-busy={exporting}><Download className="h-4 w-4" aria-hidden="true" /><span>{exporting ? 'Preparing…' : 'Export CSV'}</span></Button>
            <Link to={`/attendance/report?${reportQuery}`} className={buttonClass('secondary')}><Printer className="h-4 w-4" aria-hidden="true" /><span>Printable report</span></Link>
          </>
        )}
      />
      <FilterChips label="Attendance view" options={TABS} value={tab} onChange={setTab} />
      <Card className="grid gap-4 p-4 sm:grid-cols-2 lg:grid-cols-4">
        {tab === 'daily' && <TextField label="Date" type="date" max={today} value={date} onChange={(e) => e.target.value && setDate(e.target.value)} />}
        {tab === 'monthly' && <TextField label="Month" type="month" max={monthOf(today)} value={month} onChange={(e) => e.target.value && setMonth(e.target.value)} />}
        {(tab === 'absentees' || tab === 'changes') && (
          <>
            <TextField label="From" type="date" max={range.end} value={range.start} onChange={(e) => e.target.value && setRange((r) => ({ ...r, start: e.target.value }))} />
            <TextField label="To" type="date" max={today} value={range.end} onChange={(e) => e.target.value && setRange((r) => ({ ...r, end: e.target.value }))} />
          </>
        )}
        {tab === 'absentees' && <TextField label="At least this many absences" type="number" min="1" value={minAbsences} onChange={(e) => setMinAbsences(Math.max(Number(e.target.value) || 1, 1))} />}
        <SelectField label="Grade" value={grade} onChange={(e) => setGrade(e.target.value)} options={[{ value: '', label: 'All grades' }, ...options.data.grades.map((g) => ({ value: g, label: g }))]} />
        <SelectField label="Section" value={section} onChange={(e) => setSection(e.target.value)} options={[{ value: '', label: 'All sections' }, ...options.data.sections.map((s) => ({ value: s, label: s }))]} />
        <SelectField label="Academic session" value={yearId} onChange={(e) => setYearId(e.target.value)} options={[{ value: '', label: 'Current session' }, ...options.data.academic_years.map((y) => ({ value: String(y.id), label: y.label }))]} />
      </Card>

      {tab === 'daily' && <DailyTab key={version} filters={filters} date={date} onOpen={setOpenClass} />}
      {tab === 'monthly' && <MonthlyTab key={version} filters={filters} month={month} />}
      {tab === 'absentees' && <AbsenteesTab filters={filters} range={range} minAbsences={minAbsences} onStudent={setOpenStudent} />}
      {tab === 'changes' && <ChangesTab key={version} filters={filters} range={range} />}

      {openClass && (
        <ClassDayDialog date={date} grade={openClass.grade} section={openClass.section} onClose={() => setOpenClass(null)} onSaved={() => setVersion((v) => v + 1)} />
      )}
      {openStudent && <StudentHistoryDialog student={openStudent} range={range} onClose={() => setOpenStudent(null)} />}
    </div>
  );
}
