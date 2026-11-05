import React, { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, Download, GraduationCap, Plus, Search } from 'lucide-react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import PdfButton from '../components/PdfButton';
import StatCard from '../components/StatCard';
import StudentPicker from '../components/StudentPicker';
import Button from '../components/ui/Button';
import { SelectField, TextField } from '../components/ui/Field';
import Modal from '../components/ui/Modal';
import { Badge, Card, PageHeader } from '../components/ui/Page';
import { EmptyState, ErrorNotice } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import { apiErrorMessage } from '../lib/errors';
import { examKey, examLabel, examParams, promotionBadge, promotionStyle } from '../lib/exams';

const SUBJECT_OPTIONS = ['English', 'Urdu', 'Mathematics', 'Science', 'Islamiat', 'Pakistan Studies'].map((subject) => ({ value: subject, label: subject }));
const EXAM_TYPE_OPTIONS = [
  { value: 'Final Term', label: 'Final Term' },
  { value: 'Midterm', label: 'Midterm' },
];
const FORM_ID = 'marks-form';
const GRADE_TONES = { 'A+': 'good', A: 'good', B: 'info', C: 'warn', D: 'warn' };

function MarksDialog({ student, examType, onClose, onSaved }) {
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

export default function Results() {
  const [student, setStudent] = useState(null);
  const [studentData, setStudentData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState('');
  // The exam being viewed. Null means the student's latest.
  const [selectedExam, setSelectedExam] = useState(null);
  const [entering, setEntering] = useState(false);
  const toast = useToast();

  const fetchResults = async () => {
    if (!student) return;
    try {
      setLoading(true);
      setLoadError('');
      const res = await api.getStudentResults(student.id, examParams(selectedExam));
      setStudentData(res.data);
    } catch (err) {
      setStudentData(null);
      setLoadError(apiErrorMessage(err, 'Could not load marks. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, [student?.id, selectedExam]);

  const handleChooseStudent = (chosen) => {
    setSelectedExam(null);
    setStudentData(null);
    setLoadError('');
    setStudent(chosen);
  };

  const handleSelectExam = (key) => {
    const options = studentData?.available_exams || [];
    setSelectedExam(options.find((option) => examKey(option) === key) || null);
  };

  const handleMarksSaved = (form) => {
    setEntering(false);
    toast.success(`${form.subject} marks saved for ${student.name}.`);
    // New marks always go into the current year, so show that year's copy of this exam.
    setSelectedExam({ exam_type: form.exam_type });
  };

  const results = studentData?.results || [];
  const summary = studentData?.summary || {};
  const promotion = studentData?.promotion;
  const exam = studentData?.exam;
  const availableExams = studentData?.available_exams || [];
  const hasMarks = results.length > 0;
  const badge = promotionBadge(promotion);

  const columns = [
    { header: 'Subject', mobile: 'title', render: (row) => <span className="font-bold text-slate-900">{row.subject}</span> },
    { header: 'Marks', render: (row) => `${row.marks_obtained} of ${row.total_marks}` },
    { header: 'Percentage', render: (row) => `${row.percentage}%` },
    { header: 'Grade', render: (row) => <Badge tone={GRADE_TONES[row.grade] || 'bad'}>{row.grade}</Badge> },
    { header: 'Result', render: (row) => (row.passed ? (
      <span className="inline-flex items-center gap-1 font-semibold text-emerald-800"><CheckCircle2 className="h-4 w-4" aria-hidden="true" /> Pass</span>
    ) : (
      <span className="inline-flex items-center gap-1 font-semibold text-rose-800"><AlertCircle className="h-4 w-4" aria-hidden="true" /> Fail</span>
    )) },
  ];

  return (
    <div className="space-y-5">
      <PageHeader
        title="Exam Results"
        subtitle="Enter marks, see grades and promotion, and print report cards."
        actions={student && (
          <>
            <Button variant="secondary" onClick={() => setEntering(true)}><Plus className="h-4 w-4" aria-hidden="true" /><span>Enter Marks</span></Button>
            {hasMarks && (
              <PdfButton variant="primary" fetchPdf={() => api.getReportCardPdf(student.id, examParams(exam))}>
                <Download className="h-4 w-4" aria-hidden="true" />
                <span>Report Card</span>
              </PdfButton>
            )}
          </>
        )}
      />

      <Card className="grid grid-cols-1 gap-4 p-4 md:grid-cols-2">
        <StudentPicker student={student} onChange={handleChooseStudent} />
        {availableExams.length > 0 && (
          <SelectField
            label="Exam"
            value={exam ? examKey(exam) : ''}
            onChange={(event) => handleSelectExam(event.target.value)}
            options={availableExams.map((option) => ({ value: examKey(option), label: examLabel(option) }))}
          />
        )}
      </Card>

      {!student && (
        <Card>
          <EmptyState icon={Search} title="Choose a student" message="Search above by name or roll number to see their marks." />
        </Card>
      )}

      {student && (
        <>
          {hasMarks && !loading && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <StatCard title="Total marks" value={`${summary.total_obtained} of ${summary.total_max}`} icon={GraduationCap} color="blue" />
              <StatCard title="Percentage" value={`${summary.percentage}%`} color="blue" />
              <div className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div>
                  <p className="text-sm font-semibold text-slate-600">Overall grade</p>
                  <p className="mt-1 text-2xl font-bold text-navy-900">{summary.grade}</p>
                </div>
                {badge && <span className={`rounded-xl border px-3 py-1 text-sm font-semibold ${promotionStyle(promotion.status)}`}>{badge}</span>}
              </div>
            </div>
          )}

          {hasMarks && !loading && promotion && promotion.status !== 'promoted' && (
            <div className="space-y-0.5 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
              {promotion.reasons.length > 0
                ? promotion.reasons.map((reason) => <p key={reason}>{reason}</p>)
                : <p>{promotion.label}.</p>}
              {promotion.retake_eligible && <p className="font-semibold">Eligible for the retake examination.</p>}
            </div>
          )}

          <Card className="overflow-hidden">
            <div className="flex items-center justify-between gap-3 border-b border-slate-200 p-4">
              <h2 className="text-base font-bold text-slate-900">Marks by subject</h2>
              {exam && <span className="text-sm text-slate-600">{examLabel(exam)}</span>}
            </div>
            <DataTable
              columns={columns}
              rows={results}
              loading={loading}
              error={loadError}
              onRetry={fetchResults}
              loadingLabel="Loading marks…"
              emptyState={{
                icon: GraduationCap,
                title: 'No marks yet',
                message: `No marks are recorded for ${student.name}.`,
                action: <Button onClick={() => setEntering(true)}><Plus className="h-4 w-4" aria-hidden="true" /><span>Enter Marks</span></Button>,
              }}
            />
          </Card>
        </>
      )}

      {entering && <MarksDialog student={student} examType={exam?.exam_type} onClose={() => setEntering(false)} onSaved={handleMarksSaved} />}
    </div>
  );
}
