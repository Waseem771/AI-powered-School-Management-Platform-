import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import AttendanceSheet, { ChangeList, TallyBar } from './AttendanceSheet';
import Button from './ui/Button';
import { TextField } from './ui/Field';
import Modal from './ui/Modal';
import { Badge } from './ui/Page';
import { ErrorNotice, ErrorState, LoadingState } from './ui/States';
import { useToast } from './ui/Toast';
import {
  classLabel, correctionCount, entriesFrom, longDate, marksFrom, rateText, savingProblem, statusLabel, statusTone,
} from '../lib/attendance';
import { apiErrorMessage } from '../lib/errors';
import { useLoad } from '../lib/useLoad';

/** An administrator's view of one class on one day: record what is missing, or correct what was saved. */
export function ClassDayDialog({ date, grade, section, onClose, onSaved }) {
  const toast = useToast();
  const [day, setDay] = useState(null);
  const [marks, setMarks] = useState({});
  const [reason, setReason] = useState('');
  const [state, setState] = useState({ loading: true, error: '' });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setState({ loading: true, error: '' });
    api.getAttendanceClassDay({ date, grade, section }, { signal: controller.signal })
      .then((res) => {
        setDay(res.data);
        setMarks(marksFrom(res.data.students));
        setState({ loading: false, error: '' });
      })
      .catch((error) => {
        if (error.code !== 'ERR_CANCELED') setState({ loading: false, error: apiErrorMessage(error, 'Could not load this class.') });
      });
    return () => controller.abort();
  }, [date, grade, section, attempt]);

  const students = day?.students ?? [];
  const corrections = correctionCount(students, marks);
  const problem = savingProblem(students, marks, reason, false);
  const FORM = 'class-day-form';

  const handleSave = async () => {
    if (problem) {
      setSaveError(problem);
      return;
    }
    setSaving(true);
    setSaveError('');
    try {
      const res = await api.correctAttendanceClassDay({ date, grade, section, entries: entriesFrom(students, marks), reason: corrections ? reason : undefined });
      setDay(res.data);
      setMarks(marksFrom(res.data.students));
      setReason('');
      toast.success(`Saved: ${res.data.created} new, ${res.data.corrected} corrected.`);
      onSaved?.();
    } catch (error) {
      setSaveError(apiErrorMessage(error, 'Attendance was not saved. Please try again.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={`${classLabel(grade, section)} · ${longDate(date)}`}
      description="Students with nothing selected have no record. They are not counted as absent."
      size="xl"
      busy={saving}
      onClose={onClose}
      footer={(
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Close</Button>
          <Button onClick={handleSave} disabled={saving || state.loading || !!state.error} aria-busy={saving} id={FORM}>{saving ? 'Saving…' : 'Save Changes'}</Button>
        </>
      )}
    >
      {state.loading && <LoadingState label="Loading class…" />}
      {state.error && <ErrorState message={state.error} onRetry={() => setAttempt((n) => n + 1)} />}
      {day && !state.loading && !state.error && (
        <>
          <TallyBar students={students} marks={marks} />
          {students.length === 0 ? (
            <p className="text-sm text-slate-600">This class has no students.</p>
          ) : (
            <div className="-mx-5 max-h-[50dvh] overflow-y-auto border-y border-slate-200">
              <AttendanceSheet students={students} marks={marks} onMark={(id, status) => setMarks((m) => ({ ...m, [id]: status }))} disabled={saving} />
            </div>
          )}
          {corrections > 0 && (
            <TextField label={`Reason for correcting ${corrections} saved ${corrections === 1 ? 'record' : 'records'}`} value={reason} maxLength={300} onChange={(e) => setReason(e.target.value)} />
          )}
          <ErrorNotice>{saveError}</ErrorNotice>
          <ChangeList changes={day.changes} />
        </>
      )}
    </Modal>
  );
}

/** One student's recorded days and corrections. */
export function StudentHistoryDialog({ student, range, onClose }) {
  const { data, loading, error, reload } = useLoad(
    (request) => api.getStudentAttendance(student.id, { start: range?.start || undefined, end: range?.end || undefined }, request),
    `student-history-${student.id}-${range?.start}-${range?.end}`,
    'Could not load this student\'s attendance.',
  );
  return (
    <Modal title={student.name} description={`Roll no. ${student.roll_number} · ${classLabel(student.grade, student.section)}`} size="lg" onClose={onClose}
      footer={<Button variant="ghost" onClick={onClose}>Close</Button>}>
      {loading && <LoadingState label="Loading history…" />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && (
        <>
          <p className="text-xs text-slate-600">{longDate(data.first)} to {longDate(data.last)}. Only days that were recorded are counted.</p>
          <dl className="grid grid-cols-3 gap-3 text-sm sm:grid-cols-6">
            {[['Recorded', data.days_recorded], ['Present', data.present], ['Absent', data.absent], ['Late', data.late], ['Leave', data.leave], ['Attendance', rateText(data.attendance_rate)]].map(([label, value]) => (
              <div key={label}><dt className="text-xs text-slate-600">{label}</dt><dd className="font-bold text-slate-900">{value}</dd></div>
            ))}
          </dl>
          {data.records.length === 0 ? (
            <p className="text-sm text-slate-600">No attendance was recorded for this student in this period.</p>
          ) : (
            <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200">
              {data.records.map((record) => (
                <li key={record.date} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                  <span>{longDate(record.date)}</span>
                  <span className="flex items-center gap-2"><span className="text-xs text-slate-500">{record.marked_by}</span><Badge tone={statusTone(record.status)}>{statusLabel(record.status)}</Badge></span>
                </li>
              ))}
            </ul>
          )}
          {data.changes.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
              <p className="font-bold text-slate-900">Corrections</p>
              <ul className="mt-1 space-y-1">
                {data.changes.map((change) => (
                  <li key={`${change.date}-${change.changed_at}`}>{longDate(change.date)}: {change.old_status} to {change.new_status} by {change.changed_by}. <span className="text-slate-600">Reason: {change.reason}</span></li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </Modal>
  );
}
