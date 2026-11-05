import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import { entriesToSave, markProblems, markText, startingTotal, totalProblem } from '../lib/classMarks';
import { apiErrorMessage } from '../lib/errors';
import { countLabel } from '../lib/uiState';
import { GRADES, SECTIONS } from './StudentFormDialog';
import Button from './ui/Button';
import { INPUT_CLASS, SelectField, TextField } from './ui/Field';
import Modal from './ui/Modal';
import { EmptyState, ErrorNotice, ErrorState, LoadingState } from './ui/States';

const SUBJECTS = ['English', 'Urdu', 'Mathematics', 'Science', 'Islamiat', 'Pakistan Studies'];
const toOptions = (values) => values.map((value) => ({ value, label: value }));
const SUBJECT_OPTIONS = toOptions(SUBJECTS);
const EXAM_TYPE_OPTIONS = toOptions(['Final Term', 'Midterm']);
const FORM_ID = 'marks-form';
const CLASS_FORM_ID = 'class-marks-form';

export function MarksDialog({ student, examType, onClose, onSaved }) {
  const [form, setForm] = useState({ subject: 'Mathematics', marks_obtained: '', total_marks: 100, exam_type: examType || 'Final Term' });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const field = (key) => ({ value: form[key], onChange: (event) => setForm({ ...form, [key]: event.target.value }) });

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSaving(true);
    try {
      await api.enterMarks({
        student_id: student.id,
        subject: form.subject,
        marks_obtained: parseFloat(form.marks_obtained),
        total_marks: parseFloat(form.total_marks),
        exam_type: form.exam_type,
      });
      onSaved(form);
    } catch (err) {
      setError(apiErrorMessage(err, 'The marks could not be saved. Please try again.'));
      setSaving(false);
    }
  };

  return (
    <Modal
      title="Enter Marks"
      description={student.name}
      busy={saving}
      onClose={onClose}
      footer={(
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button type="submit" form={FORM_ID} disabled={saving}>{saving ? 'Saving…' : 'Save Marks'}</Button>
        </>
      )}
    >
      <ErrorNotice>{error}</ErrorNotice>
      <form id={FORM_ID} onSubmit={handleSubmit} className="space-y-4">
        <SelectField label="Subject" options={SUBJECT_OPTIONS} {...field('subject')} />
        <div className="grid grid-cols-2 gap-4">
          <TextField label="Marks obtained" type="number" step="0.5" min="0" max={form.total_marks} required {...field('marks_obtained')} />
          <TextField label="Total marks" type="number" step="any" min="1" max="1000" required {...field('total_marks')} />
        </div>
        <SelectField label="Exam" options={EXAM_TYPE_OPTIONS} {...field('exam_type')} />
      </form>
    </Modal>
  );
}

/** One subject for a whole class. Blank boxes are left alone, and if anything is wrong nothing is saved. */
export function ClassMarksDialog({ onClose, onSaved }) {
  const [filters, setFilters] = useState({ grade: GRADES[0], section: SECTIONS[0], subject: SUBJECTS[0], exam_type: EXAM_TYPE_OPTIONS[0].value });
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState('100');
  const [sheetSession, setSheetSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [saveError, setSaveError] = useState('');
  const [saving, setSaving] = useState(false);
  const filter = (key) => ({ value: filters[key], onChange: (event) => setFilters({ ...filters, [key]: event.target.value }) });

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setLoadError('');
    setSaveError('');
    api.getClassMarks(filters, { signal: controller.signal })
      .then((res) => {
        setRows(res.data.students.map((student) => ({ ...student, mark: markText(student.marks_obtained) })));
        setTotal(String(startingTotal(res.data.students)));
        setSheetSession(res.data.session);
        setLoading(false);
      })
      .catch((err) => {
        if (err.code === 'ERR_CANCELED') return;
        setRows([]);
        setLoadError(apiErrorMessage(err, 'This class could not be loaded. Please try again.'));
        setLoading(false);
      });
    return () => controller.abort();
  }, [filters, attempt]);

  const problems = useMemo(() => markProblems(rows, total), [rows, total]);
  const entries = useMemo(() => entriesToSave(rows), [rows]);
  const setMark = (id, mark) => setRows((current) => current.map((row) => (row.id === id ? { ...row, mark } : row)));

  const handleSubmit = async (event) => {
    event.preventDefault();
    const badTotal = totalProblem(total);
    if (badTotal) {
      setSaveError(badTotal);
      return;
    }
    if (Object.keys(problems).length > 0) {
      setSaveError('Please correct the marks shown in red. Nothing has been saved.');
      return;
    }
    if (entries.length === 0) {
      setSaveError('Enter at least one mark.');
      return;
    }
    setSaveError('');
    setSaving(true);
    try {
      await api.saveClassMarks({ subject: filters.subject, exam_type: filters.exam_type, total_marks: Number(total), entries });
      onSaved(`${filters.subject} marks saved for ${countLabel(entries.length, 'student')} in ${filters.grade}-${filters.section}.`);
    } catch (err) {
      setSaveError(`${apiErrorMessage(err, 'The marks could not be saved.')} Nothing has been saved.`);
      setSaving(false);
    }
  };

  return (
    <Modal
      title="Enter Marks for a Class"
      description={sheetSession ? `Saved to the ${sheetSession} session. Boxes left blank are not changed.` : 'Boxes left blank are not changed.'}
      size="xl"
      busy={saving}
      onClose={onClose}
      footer={(
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button type="submit" form={CLASS_FORM_ID} disabled={saving || loading || rows.length === 0}>
            {saving ? 'Saving…' : `Save ${countLabel(entries.length, 'mark')}`}
          </Button>
        </>
      )}
    >
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <SelectField label="Grade" options={toOptions(GRADES)} {...filter('grade')} />
        <SelectField label="Section" options={toOptions(SECTIONS)} {...filter('section')} />
        <SelectField label="Subject" options={SUBJECT_OPTIONS} {...filter('subject')} />
        <SelectField label="Exam" options={EXAM_TYPE_OPTIONS} {...filter('exam_type')} />
      </div>

      <ErrorNotice>{saveError}</ErrorNotice>

      {loading && <LoadingState label="Loading the class…" />}
      {!loading && loadError && <ErrorState message={loadError} onRetry={() => setAttempt((current) => current + 1)} />}
      {!loading && !loadError && rows.length === 0 && <EmptyState title="No current students in this class" />}
      {!loading && !loadError && rows.length > 0 && (
        <form id={CLASS_FORM_ID} onSubmit={handleSubmit} noValidate className="space-y-3">
          <div className="max-w-40">
            <TextField label="Total marks" type="number" min="1" max="1000" value={total} onChange={(event) => setTotal(event.target.value)} />
          </div>
          <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200">
            {rows.map((row) => (
              <li key={row.id} className="flex items-center justify-between gap-3 px-3 py-2">
                <label htmlFor={`mark-${row.id}`} className="min-w-0 text-sm">
                  <span className="block truncate font-semibold text-slate-900">{row.name}</span>
                  <span className="font-mono text-xs text-slate-600">#{row.roll_number}</span>
                  {problems[row.id] && <span className="block text-xs font-semibold text-rose-800">{problems[row.id]}</span>}
                </label>
                <input
                  id={`mark-${row.id}`}
                  type="text"
                  inputMode="decimal"
                  autoComplete="off"
                  value={row.mark}
                  aria-invalid={Boolean(problems[row.id])}
                  onChange={(event) => setMark(row.id, event.target.value)}
                  className={`${INPUT_CLASS} w-24 shrink-0 text-right ${problems[row.id] ? 'border-rose-600' : ''}`}
                />
              </li>
            ))}
          </ul>
        </form>
      )}
    </Modal>
  );
}
