import React, { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ChevronRight, Download, Edit2, GraduationCap, Plus, Receipt } from 'lucide-react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import { IssueChallanDialog, PaymentHistoryDialog, RecordPaymentDialog } from '../components/FeeDialogs';
import { invoiceColumns } from '../components/invoiceColumns';
import { MarksDialog } from '../components/MarksDialogs';
import PdfButton from '../components/PdfButton';
import StudentFormDialog from '../components/StudentFormDialog';
import Button from '../components/ui/Button';
import { SelectField } from '../components/ui/Field';
import { Badge, Card } from '../components/ui/Page';
import { ErrorState, LoadingState } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import { examKey, examLabel, examParams, promotionBadge, promotionStyle } from '../lib/exams';
import { formatRupees } from '../lib/fees';
import { MODEL_NOTE, bandLabel, bandStyle, feeFollowUpText, scoreText } from '../lib/risk';
import { useLoad } from '../lib/useLoad';

const GRADE_TONES = { 'A+': 'good', A: 'good', B: 'info', C: 'warn', D: 'warn' };

function Fact({ label, children }) {
  return (
    <div>
      <dt className="text-xs font-semibold text-slate-600">{label}</dt>
      <dd className="text-sm text-slate-900">{children}</dd>
    </div>
  );
}

function Section({ title, actions, children }) {
  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 p-4">
        <h2 className="text-base font-bold text-slate-900">{title}</h2>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {children}
    </Card>
  );
}

function FeesSection({ student, reloadKey, onChanged }) {
  const [issuing, setIssuing] = useState(false);
  const [paying, setPaying] = useState(null);
  const [viewing, setViewing] = useState(null);
  const toast = useToast();
  const invoices = useLoad((options) => api.getFees({ student_id: student.id }, options), `${student.id}-${reloadKey}`, 'Fee records could not be loaded.');
  const summary = useLoad((options) => api.getStudentFeeSummary(student.id, options), `${student.id}-${reloadKey}`, 'Fee totals could not be loaded.');
  const rows = invoices.data || [];
  const totals = summary.data;
  const isArchived = Boolean(student.archived_at);
  const issueButton = !isArchived && <Button variant="secondary" onClick={() => setIssuing(true)}><Plus className="h-4 w-4" aria-hidden="true" /><span>Issue Challan</span></Button>;
  const named = (invoice) => ({ ...invoice, student_name: student.name });

  return (
    <Section title="Fees" actions={issueButton}>
      {totals && (
        <dl className="grid grid-cols-2 gap-3 border-b border-slate-200 p-4 sm:grid-cols-4">
          <Fact label="Billed">{formatRupees(totals.invoiced)}</Fact>
          <Fact label="Paid">{formatRupees(totals.collected)}</Fact>
          <Fact label="Still owed"><b>{formatRupees(totals.outstanding)}</b></Fact>
          <Fact label="Overdue">{formatRupees(totals.overdue)}</Fact>
        </dl>
      )}
      <DataTable
        columns={invoiceColumns({ showStudent: false, onPay: (invoice) => setPaying(named(invoice)), onHistory: (invoice) => setViewing(named(invoice)) })}
        rows={rows}
        loading={invoices.loading && rows.length === 0}
        error={invoices.error}
        onRetry={invoices.reload}
        loadingLabel="Loading fee records…"
        emptyState={{ icon: Receipt, title: 'No challans yet', message: `No challan has been issued to ${student.name}.` }}
      />
      {issuing && (
        <IssueChallanDialog
          initialStudent={student}
          onClose={() => setIssuing(false)}
          onIssued={(message) => { setIssuing(false); toast.success(message); onChanged(); }}
        />
      )}
      {paying && <RecordPaymentDialog invoice={paying} onClose={() => setPaying(null)} onRecorded={onChanged} />}
      {viewing && <PaymentHistoryDialog invoice={viewing} onClose={() => setViewing(null)} />}
    </Section>
  );
}

function ResultsSection({ student, reloadKey, onChanged }) {
  const [selectedExam, setSelectedExam] = useState(null);
  const [entering, setEntering] = useState(false);
  const toast = useToast();
  const key = `${student.id}-${selectedExam ? examKey(selectedExam) : 'latest'}-${reloadKey}`;
  const report = useLoad((options) => api.getStudentResults(student.id, examParams(selectedExam), options), key, 'Marks could not be loaded.');
  const data = report.data;
  const exam = data?.exam;
  const rows = data?.results || [];
  const options = data?.available_exams || [];
  const badge = promotionBadge(data?.promotion);
  const isArchived = Boolean(student.archived_at);

  const columns = [
    { header: 'Subject', mobile: 'title', render: (row) => <span className="font-bold text-slate-900">{row.subject}</span> },
    { header: 'Marks', render: (row) => `${row.marks_obtained} of ${row.total_marks}` },
    { header: 'Percentage', render: (row) => `${row.percentage}%` },
    { header: 'Grade', render: (row) => <Badge tone={GRADE_TONES[row.grade] || 'bad'}>{row.grade}</Badge> },
    { header: 'Result', render: (row) => (row.passed ? <span className="font-semibold text-emerald-800">Pass</span> : <span className="font-semibold text-rose-800">Fail</span>) },
  ];

  return (
    <Section
      title="Exam Results"
      actions={(
        <>
          {!isArchived && <Button variant="secondary" onClick={() => setEntering(true)}><Plus className="h-4 w-4" aria-hidden="true" /><span>Enter Marks</span></Button>}
          {rows.length > 0 && (
            <PdfButton fetchPdf={() => api.getReportCardPdf(student.id, examParams(exam))}>
              <Download className="h-4 w-4" aria-hidden="true" />
              <span>Report Card</span>
            </PdfButton>
          )}
        </>
      )}
    >
      {options.length > 1 && (
        <div className="max-w-xs border-b border-slate-200 p-4">
          <SelectField
            label="Exam"
            value={exam ? examKey(exam) : ''}
            onChange={(event) => setSelectedExam(options.find((option) => examKey(option) === event.target.value) || null)}
            options={options.map((option) => ({ value: examKey(option), label: examLabel(option) }))}
          />
        </div>
      )}
      {rows.length > 0 && data.summary && (
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-slate-200 p-4 text-sm">
          {exam && <span className="text-slate-600">{examLabel(exam)}</span>}
          <span>Total <b>{data.summary.total_obtained} of {data.summary.total_max}</b></span>
          <span>Percentage <b>{data.summary.percentage}%</b></span>
          <span>Grade <b>{data.summary.grade}</b></span>
          {badge && <span className={`rounded-xl border px-3 py-0.5 font-semibold ${promotionStyle(data.promotion.status)}`}>{badge}</span>}
        </div>
      )}
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(row) => row.id}
        loading={report.loading && rows.length === 0}
        error={report.error}
        onRetry={report.reload}
        loadingLabel="Loading marks…"
        emptyState={{ icon: GraduationCap, title: 'No marks yet', message: `No marks are recorded for ${student.name}.` }}
      />
      {entering && (
        <MarksDialog
          student={student}
          examType={exam?.exam_type}
          onClose={() => setEntering(false)}
          onSaved={(form) => {
            setEntering(false);
            toast.success(`${form.subject} marks saved for ${student.name}.`);
            setSelectedExam({ exam_type: form.exam_type });
            onChanged();
          }}
        />
      )}
    </Section>
  );
}

function EstimateSection({ student, reloadKey }) {
  const detail = useLoad((options) => api.getStudentRiskDetail(student.id, options), `${student.id}-${reloadKey}`, 'The estimate could not be loaded.');
  const data = detail.data;
  const assessment = data?.risk_assessment;
  const feeText = feeFollowUpText(data?.fee_follow_up);

  return (
    <Section title="Academic Early Warning">
      {detail.loading && !data && <LoadingState label="Loading the estimate…" />}
      {detail.error && <ErrorState message={detail.error} onRetry={detail.reload} />}
      {assessment && (
        <div className="space-y-3 p-4 text-sm">
          <div className="flex flex-wrap items-center gap-3">
            <span className={`rounded-full border px-3 py-1 text-xs font-bold ${bandStyle(assessment.risk_category).badge}`}>{bandLabel(assessment.risk_category)}</span>
            {assessment.risk_score !== null && <span className="text-slate-700">{scoreText(assessment.risk_score)}</span>}
          </div>
          {assessment.top_reasons.length > 0 && (
            <ul className="list-inside list-disc space-y-1 text-slate-800">
              {assessment.top_reasons.map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
          )}
          {feeText && <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-amber-900"><b>{feeText}.</b> For the accounts office. This does not affect the academic estimate.</p>}
          <p className="text-xs text-slate-600">{MODEL_NOTE}</p>
        </div>
      )}
    </Section>
  );
}

export default function StudentProfile() {
  const { id } = useParams();
  const [editing, setEditing] = useState(false);
  const [changes, setChanges] = useState(0);
  const toast = useToast();
  const profile = useLoad((options) => api.getStudent(id, options), `${id}-${changes}`, 'This student could not be loaded.');
  const student = profile.data;
  const onChanged = () => setChanges((current) => current + 1);

  const back = (
    <Link to="/students" className="inline-flex min-h-11 items-center gap-1 text-sm font-semibold text-brand-700 hover:underline">
      <ArrowLeft className="h-4 w-4" aria-hidden="true" /> <span>All students</span>
    </Link>
  );

  if (profile.loading && !student) return <div>{back}<LoadingState label="Loading the student…" /></div>;
  if (profile.error || !student) {
    return <div>{back}<Card><ErrorState title="This student could not be opened" message={profile.error} onRetry={profile.reload} /></Card></div>;
  }

  return (
    <div className="space-y-5">
      {back}
      <Card className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-navy-900">{student.name}</h1>
              {student.archived_at && <Badge tone="warn">Archived</Badge>}
            </div>
            <p className="text-sm text-slate-600">Roll #{student.roll_number} &bull; {student.grade} - {student.section}</p>
          </div>
          <Button variant="secondary" onClick={() => setEditing(true)}><Edit2 className="h-4 w-4" aria-hidden="true" /><span>Edit</span></Button>
        </div>
        <dl className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Fact label="Guardian">{student.guardian_name}</Fact>
          <Fact label="Phone"><a href={`tel:${student.phone}`} className="inline-flex min-h-11 items-center text-brand-700 underline-offset-2 hover:underline">{student.phone}</a></Fact>
          <Fact label="Date of birth">{student.dob || 'Not recorded'}</Fact>
        </dl>
      </Card>

      <FeesSection student={student} reloadKey={changes} onChanged={onChanged} />
      <ResultsSection student={student} reloadKey={changes} onChanged={onChanged} />
      {!student.archived_at && <EstimateSection student={student} reloadKey={changes} />}

      {editing && (
        <StudentFormDialog
          student={student}
          onClose={() => setEditing(false)}
          onSaved={(message) => { setEditing(false); toast.success(message); onChanged(); }}
        />
      )}
      <Link to="/at-risk" className="inline-flex min-h-11 items-center gap-1 text-sm font-semibold text-brand-700 hover:underline">
        <span>See all students' estimates</span> <ChevronRight className="h-4 w-4" aria-hidden="true" />
      </Link>
    </div>
  );
}
