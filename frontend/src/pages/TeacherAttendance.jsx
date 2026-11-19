import React, { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, CheckCheck, Save } from 'lucide-react';
import { api } from '../api/client';
import AttendanceSheet, { ChangeList, TallyBar } from '../components/AttendanceSheet';
import Button from '../components/ui/Button';
import { TextField } from '../components/ui/Field';
import { Badge, Card, PageHeader } from '../components/ui/Page';
import { ErrorNotice, ErrorState, LoadingState } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import {
  classLabel, correctionCount, entriesFrom, longDate, marksFrom, savingProblem, shiftDate, stateInfo,
} from '../lib/attendance';
import { apiErrorMessage } from '../lib/errors';

export default function TeacherAttendance() {
  const { id } = useParams();
  const toast = useToast();
  const [searchParams] = useSearchParams();
  const requestedDate = /^\d{4}-\d{2}-\d{2}$/.test(searchParams.get('date') ?? '') ? searchParams.get('date') : '';
  const [classInfo, setClassInfo] = useState(null);
  const [date, setDate] = useState('');
  const [day, setDay] = useState(null);
  const [marks, setMarks] = useState({});
  const [reason, setReason] = useState('');
  const [state, setState] = useState({ loading: true, error: '' });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [attempt, setAttempt] = useState(0);

  // The class, and the school's idea of today, come from the server.
  useEffect(() => {
    const controller = new AbortController();
    api.getMyClass(id, { signal: controller.signal })
      .then((res) => {
        setClassInfo(res.data);
        setDate((current) => current || requestedDate || res.data.today);
      })
      .catch((error) => {
        if (error.code !== 'ERR_CANCELED') setState({ loading: false, error: apiErrorMessage(error, 'Could not open this class.') });
      });
    return () => controller.abort();
  }, [id, attempt]);

  useEffect(() => {
    if (!date) return undefined;
    const controller = new AbortController();
    setState({ loading: true, error: '' });
    setSaveError('');
    api.getClassAttendance(id, date, { signal: controller.signal })
      .then((res) => {
        setDay(res.data);
        setMarks(marksFrom(res.data.students));
        setReason('');
        setState({ loading: false, error: '' });
      })
      .catch((error) => {
        if (error.code !== 'ERR_CANCELED') setState({ loading: false, error: apiErrorMessage(error, 'Could not load attendance for this date.') });
      });
    return () => controller.abort();
  }, [id, date, attempt]);

  if (!classInfo && state.error) return <ErrorState title="This class could not be opened" message={state.error} onRetry={() => { setState({ loading: true, error: '' }); setAttempt((n) => n + 1); }} />;
  if (!classInfo || !date) return <LoadingState label="Loading the class…" />;

  const earliest = shiftDate(classInfo.today, -classInfo.edit_window_days);
  const students = day?.students ?? [];
  const corrections = correctionCount(students, marks);
  const problem = savingProblem(students, marks, reason);
  const closed = !classInfo.is_current_session;
  const saved = day ? stateInfo(day.state) : null;

  const handleMark = (studentId, status) => setMarks((current) => ({ ...current, [studentId]: status }));
  const markAllPresent = () => setMarks((current) => ({ ...Object.fromEntries(students.map((s) => [s.id, 'present'])), ...Object.fromEntries(Object.entries(current).filter(([, v]) => v)) }));

  const handleSave = async () => {
    if (problem) {
      setSaveError(problem);
      return;
    }
    setSaving(true);
    setSaveError('');
    try {
      const res = await api.saveClassAttendance(id, { date, entries: entriesFrom(students, marks), reason: corrections ? reason : undefined });
      setDay({ ...res.data, can_edit: true });
      setMarks(marksFrom(res.data.students));
      setReason('');
      const { created, corrected } = res.data;
      toast.success(corrected ? `Attendance saved. ${corrected} correction${corrected === 1 ? '' : 's'} recorded.` : `Attendance saved for ${created} student${created === 1 ? '' : 's'}.`);
    } catch (error) {
      setSaveError(apiErrorMessage(error, 'Attendance was not saved. Please try again.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5">
      <Link to={`/teacher/classes/${id}`} className="inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold text-brand-700 hover:underline">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> {classLabel(classInfo.grade, classInfo.section)}
      </Link>
      <PageHeader title="Daily Attendance" subtitle={`${classLabel(classInfo.grade, classInfo.section)} · ${classInfo.academic_year}`} />

      <Card className="space-y-4 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-full sm:w-56">
            <TextField label="Date" type="date" value={date} min={earliest} max={classInfo.today} onChange={(event) => event.target.value && setDate(event.target.value)} />
          </div>
          <Button variant="secondary" onClick={() => setDate(classInfo.today)} disabled={date === classInfo.today}>Today</Button>
          <p className="pb-2 text-sm text-slate-700">{longDate(date)}</p>
        </div>
        <p className="text-xs text-slate-600">You can record or correct the last {classInfo.edit_window_days} days. For older dates, ask the school office.</p>
        {closed && <ErrorNotice>This class belongs to a session that is closed, so attendance cannot be changed.</ErrorNotice>}
      </Card>

      {state.error && !state.loading ? (
        <Card><ErrorState message={state.error} onRetry={() => setAttempt((n) => n + 1)} /></Card>
      ) : state.loading ? (
        <Card><LoadingState label="Loading attendance…" /></Card>
      ) : (
        <Card>
          <div className="space-y-3 border-b border-slate-200 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm text-slate-800">
                {saved && <Badge tone={saved.tone}>{saved.label}{day.state === 'partial' ? ` (${day.recorded} of ${day.enrolled})` : ''}</Badge>}
                {day.state === 'not_submitted' && <span className="ml-2 text-slate-600">Nothing saved for this date yet.</span>}
              </p>
              <Button variant="secondary" onClick={markAllPresent} disabled={saving || closed || students.length === 0}>
                <CheckCheck className="h-4 w-4" aria-hidden="true" /><span>Mark unmarked as Present</span>
              </Button>
            </div>
            <TallyBar students={students} marks={marks} />
          </div>
          {students.length === 0 ? (
            <p className="p-6 text-center text-sm text-slate-600">This class has no students.</p>
          ) : (
            <AttendanceSheet students={students} marks={marks} onMark={handleMark} disabled={saving || closed} />
          )}
          <div className="space-y-3 border-t border-slate-200 p-4">
            {corrections > 0 && (
              <TextField
                label={`Reason for correcting ${corrections} saved ${corrections === 1 ? 'record' : 'records'}`}
                value={reason}
                maxLength={300}
                onChange={(event) => setReason(event.target.value)}
                hint="Corrections are kept in the attendance history with your name."
              />
            )}
            <ErrorNotice>{saveError}</ErrorNotice>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-slate-600">Students you leave unmarked are not counted as absent.</p>
              <Button onClick={handleSave} disabled={saving || closed || students.length === 0} aria-busy={saving}>
                <Save className="h-4 w-4" aria-hidden="true" /><span>{saving ? 'Saving…' : 'Save Attendance'}</span>
              </Button>
            </div>
          </div>
        </Card>
      )}
      {day && <ChangeList changes={day.changes} />}
    </div>
  );
}
