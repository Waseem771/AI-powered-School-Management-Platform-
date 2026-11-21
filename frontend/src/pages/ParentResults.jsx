import React, { useState } from 'react';
import { Download } from 'lucide-react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import ParentChildPage from '../components/ParentChildPage';
import PdfButton from '../components/PdfButton';
import StatCard from '../components/StatCard';
import { SelectField } from '../components/ui/Field';
import { Badge, Card } from '../components/ui/Page';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States';
import { examLabel, examParams, promotionBadge, promotionStyle } from '../lib/exams';
import { examFromValue, examValue } from '../lib/parent';
import { useLoad } from '../lib/useLoad';

const subjectColumns = [
  { header: 'Subject', mobile: 'title', render: (row) => <span className="font-semibold text-slate-900">{row.subject}</span> },
  { header: 'Marks', render: (row) => `${row.marks_obtained} / ${row.total_marks}` },
  { header: 'Percentage', render: (row) => `${row.percentage}%` },
  { header: 'Grade', render: (row) => <span className="font-bold text-slate-900">{row.grade}</span> },
  { header: 'Result', render: (row) => <Badge tone={row.passed ? 'good' : 'bad'}>{row.passed ? 'Pass' : 'Fail'}</Badge> },
];

const examColumns = [
  { header: 'Exam', mobile: 'title', render: (exam) => <span className="font-semibold text-slate-900">{examLabel(exam)}</span> },
  { header: 'Percentage', render: (exam) => `${exam.percentage}%` },
  { header: 'Grade', render: (exam) => <span className="font-bold text-slate-900">{exam.grade}</span> },
];

function Promotion({ promotion }) {
  const badge = promotionBadge(promotion);
  if (!badge) return null;
  return (
    <div className="space-y-1">
      <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${promotionStyle(promotion.status)}`}>{badge}</span>
      {promotion.status === 'incomplete' && <p className="text-xs text-slate-600">{promotion.label}</p>}
      {promotion.reasons?.length > 0 && (
        <ul className="list-disc pl-5 text-xs text-slate-700">
          {promotion.reasons.map((reason) => <li key={reason}>{reason}</li>)}
        </ul>
      )}
    </div>
  );
}

function ResultsBody({ child }) {
  const [chosen, setChosen] = useState('');
  const exam = chosen ? examFromValue(chosen) : null;
  const { data, loading, error, reload } = useLoad(
    (options) => api.getParentChildResults(child.id, examParams(exam), options),
    `${child.id}|${chosen}`,
    'Could not load the results. Please try again.',
  );

  if (error && !data) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <LoadingState label="Loading results…" />;

  if (!data.exam) {
    return (
      <Card>
        <EmptyState
          title="No results have been released yet"
          message="The school shows marks here after an exam is finalised. Please check again later, or ask the school office."
        />
      </Card>
    );
  }

  const { summary, promotion } = data;
  const current = examValue(data.exam);

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="w-full sm:w-72">
          <SelectField
            label="Exam"
            value={current}
            onChange={(event) => setChosen(event.target.value)}
            options={data.available_exams.map((option) => ({ value: examValue(option), label: examLabel(option) }))}
          />
        </div>
        <PdfButton fetchPdf={() => api.getParentReportCardPdf(child.id, examParams(data.exam))} title="Download the report card as a PDF">
          <Download className="h-4 w-4" aria-hidden="true" />
          <span>Report card</span>
        </PdfButton>
      </div>

      <section aria-label="Result summary" className="grid gap-4 sm:grid-cols-3">
        <StatCard title="Total marks" value={`${summary.total_obtained} / ${summary.total_max}`} subtitle={examLabel(data.exam)} />
        <StatCard title="Percentage" value={`${summary.percentage}%`} subtitle={`Grade ${summary.grade}`} color="green" />
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-semibold text-slate-600">Promotion</p>
          <div className="mt-2">
            {promotionBadge(promotion) ? <Promotion promotion={promotion} /> : <p className="text-sm text-slate-700">Decided on Final Term marks</p>}
          </div>
        </div>
      </section>

      <Card>
        <DataTable
          columns={subjectColumns}
          rows={data.results}
          rowKey={(row) => row.subject}
          loading={loading}
          error={error}
          onRetry={reload}
          loadingLabel="Loading results…"
          emptyState={{ title: 'No marks for this exam' }}
        />
      </Card>

      {data.available_exams.length > 1 && (
        <section aria-labelledby="progress-heading" className="space-y-2">
          <h2 id="progress-heading" className="text-base font-bold text-slate-900">Progress across exams</h2>
          <Card>
            <DataTable
              columns={examColumns}
              rows={data.available_exams}
              rowKey={examValue}
              emptyState={{ title: 'No exams' }}
            />
          </Card>
        </section>
      )}
    </>
  );
}

export default function ParentResults() {
  return (
    <ParentChildPage title="Exam Results" subtitle="Marks and grades for exams the school has released.">
      {(child) => <ResultsBody key={child.id} child={child} />}
    </ParentChildPage>
  );
}
