import React from 'react';
import { AlertCircle, BarChart2, GraduationCap, TrendingUp, Trophy, Users } from 'lucide-react';

const money = (value) => `Rs ${Number(value ?? 0).toLocaleString()}`;
const percent = (value) => `${value}%`;

function ChatTable({ icon: Icon, title, note, columns, rows }) {
  return (
    <div className="mt-3 rounded-xl border border-slate-200 bg-white/70 p-3 text-[11px] space-y-2">
      <div className="flex items-center gap-2 font-bold text-slate-800 text-xs">
        <Icon className="w-3.5 h-3.5" /> {title}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px] text-slate-700 border-collapse">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500">
              {columns.map((column) => (
                <th key={column.label} className={`py-1 pr-2 ${column.right ? 'text-right' : 'text-left'}`}>{column.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex} className="border-b border-slate-100">
                {columns.map((column) => (
                  <td key={column.label} className={`py-0.5 pr-2 ${column.right ? 'text-right' : ''}`}>{column.value(row)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {note && <p className="text-[10px] text-slate-500">{note}</p>}
    </div>
  );
}

const examTitle = (data) => [data.exam_type, data.academic_year, data.grade].filter(Boolean).join(' · ');

export function StudentCountsCard({ data }) {
  if (!data?.classes?.length) return null;
  return (
    <ChatTable
      icon={Users}
      title={`${data.total} current student(s)`}
      note={data.archived ? `${data.archived} archived student(s) are not counted.` : null}
      columns={[
        { label: 'Class', value: (row) => `${row.grade}-${row.section}` },
        { label: 'Students', right: true, value: (row) => row.students },
      ]}
      rows={data.classes}
    />
  );
}

export function TopStudentsCard({ data }) {
  if (!data?.students?.length) return null;
  return (
    <ChatTable
      icon={Trophy}
      title={`Top students: ${examTitle(data)}`}
      note={data.left_out_incomplete ? `${data.left_out_incomplete} student(s) with missing subjects are not ranked.` : null}
      columns={[
        { label: 'Rank', value: (row) => row.rank },
        { label: 'Name', value: (row) => row.name },
        { label: 'Roll #', value: (row) => row.roll_number },
        { label: 'Class', value: (row) => `${row.grade}-${row.section}` },
        { label: '%', right: true, value: (row) => percent(row.percentage) },
      ]}
      rows={data.students}
    />
  );
}

export function SubjectAveragesCard({ data }) {
  if (!data?.subjects?.length) return null;
  return (
    <ChatTable
      icon={BarChart2}
      title={`Subject averages: ${examTitle(data)}`}
      columns={[
        { label: 'Subject', value: (row) => row.subject },
        { label: 'Students', right: true, value: (row) => row.students },
        { label: 'Average', right: true, value: (row) => percent(row.average_percentage) },
      ]}
      rows={data.subjects}
    />
  );
}

export function MonthlyCollectionCard({ data }) {
  if (!data?.months?.length) return null;
  return (
    <ChatTable
      icon={TrendingUp}
      title="Fees by billing month"
      note="Payments count towards the month of their invoice."
      columns={[
        { label: 'Month', value: (row) => row.month },
        { label: 'Invoiced', right: true, value: (row) => money(row.invoiced) },
        { label: 'Collected', right: true, value: (row) => money(row.collected) },
        { label: 'Pending', right: true, value: (row) => money(row.outstanding) },
        { label: 'Rate', right: true, value: (row) => percent(row.collection_rate) },
      ]}
      rows={data.months}
    />
  );
}

export function AtRiskCard({ data }) {
  if (!data) return null;
  const notScored = data.not_scored ? ` ${data.not_scored} student(s) have no marks and no estimate.` : '';
  return (
    <ChatTable
      icon={AlertCircle}
      title={`${data.levels?.join(' or ')} estimated risk`}
      note={`${data.note}${notScored}`}
      columns={[
        { label: 'Name', value: (row) => row.name },
        { label: 'Roll #', value: (row) => row.roll_number },
        { label: 'Class', value: (row) => `${row.grade}-${row.section}` },
        { label: 'Level', value: (row) => row.risk_category },
        { label: 'Score', right: true, value: (row) => `${row.risk_score} of 100` },
      ]}
      rows={data.students ?? []}
    />
  );
}

export function StudentRiskCard({ data }) {
  if (!data?.estimate) return null;
  const reasons = data.estimate.top_reasons?.map((reason) => reason.text ?? String(reason)) ?? [];
  return (
    <ChatTable
      icon={GraduationCap}
      title={`Estimated risk: ${data.student.name}`}
      note={data.note}
      columns={[
        { label: 'Level', value: () => data.estimate.risk_category },
        { label: 'Score', value: () => `${data.estimate.risk_score} of 100` },
        { label: 'Main reasons', value: () => reasons.join('; ') || 'None given' },
      ]}
      rows={[data.estimate]}
    />
  );
}
