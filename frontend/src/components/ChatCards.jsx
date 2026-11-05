import React, { useState } from 'react';
import {
  AlertCircle,
  BarChart2,
  ChevronDown,
  ChevronUp,
  DollarSign,
  GraduationCap,
  Search,
  TrendingUp,
} from 'lucide-react';
import {
  AtRiskCard,
  MonthlyCollectionCard,
  StudentCountsCard,
  StudentRiskCard,
  SubjectAveragesCard,
  TopStudentsCard,
} from './ChatTables';

/* ─────────── Grade colour helper ────────────────────────────────────── */
function gradeColor(g) {
  const map = { 'A+': 'text-emerald-700 bg-emerald-50', A: 'text-green-700 bg-green-50', 'B+': 'text-teal-700 bg-teal-50', B: 'text-cyan-700 bg-cyan-50', C: 'text-yellow-700 bg-yellow-50', D: 'text-orange-700 bg-orange-50', F: 'text-red-700 bg-red-50' };
  return map[g] || 'text-slate-600 bg-slate-100';
}

/* ─────────── Rich structured-data card components ───────────────────── */
function StudentProfileCard({ data }) {
  if (!data?.found) return null;
  const s = data.student;
  return (
    <div className="mt-3 rounded-xl border border-blue-200 bg-blue-50/60 p-3 text-[11px] space-y-2">
      <div className="flex items-center gap-2 font-bold text-blue-800 text-xs">
        <GraduationCap className="w-3.5 h-3.5" />
        Student Profile
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-slate-700">
        <span className="font-semibold text-slate-500">Name</span>       <span>{s.name}</span>
        <span className="font-semibold text-slate-500">Roll #</span>     <span>{s.roll_number}</span>
        <span className="font-semibold text-slate-500">Grade</span>      <span>{s.grade} – {s.section}</span>
        {s.guardian_name && <><span className="font-semibold text-slate-500">Guardian</span><span>{s.guardian_name}</span></>}
        {s.phone         && <><span className="font-semibold text-slate-500">Phone</span>   <span>{s.phone}</span></>}
        {s.date_of_birth && <><span className="font-semibold text-slate-500">DOB</span>     <span>{s.date_of_birth}</span></>}
      </div>
    </div>
  );
}

function FeeSummaryCard({ data }) {
  const [expanded, setExpanded] = useState(false);
  if (!data?.found) return null;
  const t = data.totals;
  const pct = t.invoiced > 0 ? Math.round((t.paid / t.invoiced) * 100) : 0;
  return (
    <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50/60 p-3 text-[11px] space-y-2">
      <div className="flex items-center gap-2 font-bold text-emerald-800 text-xs">
        <DollarSign className="w-3.5 h-3.5" />
        Fee Summary — {data.student.name}
      </div>
      <div className="grid grid-cols-3 gap-2 text-center">
        {[['Invoiced', t.invoiced, 'text-slate-700'], ['Paid', t.paid, 'text-emerald-700'], ['Pending', t.pending, t.pending > 0 ? 'text-red-600' : 'text-emerald-600']].map(([l, v, cls]) => (
          <div key={l} className="rounded-lg bg-white border border-slate-200 py-1.5 px-1">
            <div className={`font-bold text-sm ${cls}`}>Rs {v.toLocaleString()}</div>
            <div className="text-slate-400 text-[10px]">{l}</div>
          </div>
        ))}
      </div>
      {/* progress bar */}
      <div className="space-y-0.5">
        <div className="flex justify-between text-[10px] text-slate-500">
          <span>Collection Rate</span><span className="font-bold">{pct}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-slate-200 overflow-hidden">
          <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${pct}%` }} />
        </div>
      </div>
      {data.invoices?.length > 0 && (
        <>
          <button onClick={() => setExpanded(e => !e)} className="flex items-center gap-1 text-[10px] text-emerald-700 font-semibold hover:underline">
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {expanded ? 'Hide' : 'Show'} {data.invoices.length} invoice(s)
          </button>
          {expanded && (
            <div className="overflow-x-auto">
              <table className="w-full text-[10px] text-slate-700 border-collapse">
                <thead>
                  <tr className="border-b border-emerald-200 text-slate-500">
                    <th className="text-left py-1 pr-2">Challan</th>
                    <th className="text-left py-1 pr-2">Month</th>
                    <th className="text-right py-1 pr-2">Amount</th>
                    <th className="text-left py-1">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.invoices.map((inv, i) => (
                    <tr key={i} className="border-b border-emerald-100/60">
                      <td className="py-0.5 pr-2 font-mono">{inv.challan_number}</td>
                      <td className="py-0.5 pr-2">{inv.month}</td>
                      <td className="py-0.5 pr-2 text-right">Rs {inv.amount.toLocaleString()}</td>
                      <td className="py-0.5">
                        <span className={`px-1.5 py-0.5 rounded-md font-semibold ${inv.status === 'paid' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                          {inv.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ResultsCard({ data }) {
  if (!data?.found || !data.results?.length) return null;
  return (
    <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50/60 p-3 text-[11px] space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 font-bold text-amber-800 text-xs">
          <BarChart2 className="w-3.5 h-3.5" />
          Results — {data.student.name}
        </div>
        {data.average_percentage != null && (
          <span className="text-[10px] font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-lg border border-amber-200">
            Avg {data.average_percentage}%
          </span>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px] text-slate-700 border-collapse">
          <thead>
            <tr className="border-b border-amber-200 text-slate-500">
              <th className="text-left py-1 pr-2">Subject</th>
              <th className="text-right py-1 pr-2">Marks</th>
              <th className="text-right py-1 pr-2">%</th>
              <th className="text-left py-1">Grade</th>
              <th className="text-left py-1">Type</th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((r, i) => {
              const pct = Math.round((r.marks_obtained / r.total_marks) * 100);
              return (
                <tr key={i} className="border-b border-amber-100/60">
                  <td className="py-0.5 pr-2 font-medium">{r.subject}</td>
                  <td className="py-0.5 pr-2 text-right">{r.marks_obtained}/{r.total_marks}</td>
                  <td className="py-0.5 pr-2 text-right">{pct}%</td>
                  <td className="py-0.5">
                    <span className={`px-1.5 py-0.5 rounded-md font-bold text-[9px] ${gradeColor(r.grade)}`}>{r.grade}</span>
                  </td>
                  <td className="py-0.5 text-slate-400 capitalize">{r.exam_type}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CollectionSummaryCard({ data }) {
  if (!data?.invoices) return null;
  const pct = data.collection_rate;
  return (
    <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50/60 p-3 text-[11px] space-y-2">
      <div className="flex items-center gap-2 font-bold text-rose-800 text-xs">
        <TrendingUp className="w-3.5 h-3.5" />
        School-wide Fee Collection
      </div>
      <div className="grid grid-cols-2 gap-2">
        {[['Total Invoiced', `Rs ${data.invoiced.toLocaleString()}`, 'text-slate-700'], ['Total Collected', `Rs ${data.paid.toLocaleString()}`, 'text-emerald-700'], ['Total Pending', `Rs ${data.pending.toLocaleString()}`, 'text-red-600'], ['Invoices', data.invoices, 'text-slate-700']].map(([l, v, cls]) => (
          <div key={l} className="rounded-lg bg-white border border-slate-200 py-2 px-2">
            <div className={`font-bold text-sm ${cls}`}>{v}</div>
            <div className="text-slate-400 text-[10px]">{l}</div>
          </div>
        ))}
      </div>
      <div className="space-y-0.5">
        <div className="flex justify-between text-[10px] text-slate-500">
          <span>Recovery Rate</span><span className="font-bold">{pct}%</span>
        </div>
        <div className="h-2 rounded-full bg-slate-200 overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: pct > 80 ? '#22c55e' : pct > 50 ? '#f59e0b' : '#ef4444' }} />
        </div>
      </div>
    </div>
  );
}

function FindStudentsCard({ data }) {
  if (!Array.isArray(data) || data.length === 0) return null;
  return (
    <div className="mt-3 rounded-xl border border-violet-200 bg-violet-50/60 p-3 text-[11px] space-y-1.5">
      <div className="flex items-center gap-2 font-bold text-violet-800 text-xs">
        <Search className="w-3.5 h-3.5" />
        {data.length} Student(s) Found
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px] text-slate-700 border-collapse">
          <thead>
            <tr className="border-b border-violet-200 text-slate-500">
              <th className="text-left py-1 pr-2">Name</th>
              <th className="text-left py-1 pr-2">Roll #</th>
              <th className="text-left py-1 pr-2">Grade</th>
              <th className="text-left py-1">Section</th>
            </tr>
          </thead>
          <tbody>
            {data.map((s, i) => (
              <tr key={i} className="border-b border-violet-100/60">
                <td className="py-0.5 pr-2 font-medium">{s.name}{s.archived ? ' (archived)' : ''}</td>
                <td className="py-0.5 pr-2 font-mono">{s.roll_number}</td>
                <td className="py-0.5 pr-2">{s.grade}</td>
                <td className="py-0.5">{s.section}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PendingStudentsCard({ data }) {
  const [expanded, setExpanded] = useState(false);
  if (!data || data.count === 0) return (
    <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50/60 p-3 text-[11px] text-emerald-700 font-semibold">
      ✅ All students are up to date — no pending fees found.
    </div>
  );
  const shown = expanded ? data.students : data.students.slice(0, 8);
  return (
    <div className="mt-3 rounded-xl border border-red-200 bg-red-50/60 p-3 text-[11px] space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 font-bold text-red-800 text-xs">
          <AlertCircle className="w-3.5 h-3.5" />
          {data.count} Student(s) with Pending Fees
          {data.grade_filter && <span className="font-normal text-red-600"> — {data.grade_filter}</span>}
        </div>
        <span className="text-[10px] font-bold text-red-700 bg-red-100 px-2 py-0.5 rounded-lg border border-red-200">
          Total Rs {data.total_pending.toLocaleString()} due
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-[10px] text-slate-700 border-collapse">
          <thead>
            <tr className="border-b border-red-200 text-slate-500">
              <th className="text-left py-1 pr-2">#</th>
              <th className="text-left py-1 pr-2">Name</th>
              <th className="text-left py-1 pr-2">Roll #</th>
              <th className="text-left py-1 pr-2">Grade</th>
              <th className="text-left py-1 pr-2">Guardian</th>
              <th className="text-left py-1 pr-2">Phone</th>
              <th className="text-right py-1 pr-2">Invoices</th>
              <th className="text-right py-1">Pending (Rs)</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((s, i) => (
              <tr key={i} className="border-b border-red-100/60 hover:bg-red-50">
                <td className="py-1 pr-2 text-slate-400">{i + 1}</td>
                <td className="py-1 pr-2 font-semibold text-slate-800">{s.name}{s.archived ? ' (archived)' : ''}</td>
                <td className="py-1 pr-2 font-mono text-slate-600">{s.roll_number}</td>
                <td className="py-1 pr-2">{s.grade}</td>
                <td className="py-1 pr-2 text-slate-500">{s.guardian_name || '—'}</td>
                <td className="py-1 pr-2 text-slate-500">{s.phone || '—'}</td>
                <td className="py-1 pr-2 text-right">
                  <span className="px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-bold">{s.pending_invoices}</span>
                </td>
                <td className="py-1 text-right font-bold text-red-700">
                  {s.pending_amount.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
          {data.students.length > 0 && (
            <tfoot>
              <tr className="border-t-2 border-red-300 bg-red-100/40 font-bold">
                <td colSpan={7} className="py-1 pr-2 text-right text-red-700 text-[10px]">Total Outstanding:</td>
                <td className="py-1 text-right text-red-800">Rs {data.total_pending.toLocaleString()}</td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>

      {/* Expand/collapse */}
      {data.students.length > 8 && (
        <button onClick={() => setExpanded(e => !e)}
          className="flex items-center gap-1 text-[10px] text-red-700 font-semibold hover:underline">
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? 'Show less' : `Show all ${data.students.length} students`}
        </button>
      )}
    </div>
  );
}

function GradeStudentsCard({ data }) {
  const [expanded, setExpanded] = useState(false);
  if (!data || data.count === 0) return null;
  const shown = expanded ? data.students : data.students.slice(0, 8);
  return (
    <div className="mt-3 rounded-xl border border-cyan-200 bg-cyan-50/60 p-3 text-[11px] space-y-2">
      <div className="flex items-center gap-2 font-bold text-cyan-800 text-xs">
        <GraduationCap className="w-3.5 h-3.5" />
        {data.count} Student(s) in {data.grade}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px] text-slate-700 border-collapse">
          <thead>
            <tr className="border-b border-cyan-200 text-slate-500">
              <th className="text-left py-1 pr-2">#</th>
              <th className="text-left py-1 pr-2">Name</th>
              <th className="text-left py-1 pr-2">Roll #</th>
              <th className="text-left py-1 pr-2">Section</th>
              <th className="text-left py-1 pr-2">Guardian</th>
              <th className="text-left py-1">Phone</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((s, i) => (
              <tr key={i} className="border-b border-cyan-100/60 hover:bg-cyan-50">
                <td className="py-1 pr-2 text-slate-400">{i + 1}</td>
                <td className="py-1 pr-2 font-semibold text-slate-800">{s.name}</td>
                <td className="py-1 pr-2 font-mono text-slate-600">{s.roll_number}</td>
                <td className="py-1 pr-2">{s.section}</td>
                <td className="py-1 pr-2 text-slate-500">{s.guardian_name || '—'}</td>
                <td className="py-1 text-slate-500">{s.phone || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.students.length > 8 && (
        <button onClick={() => setExpanded(e => !e)}
          className="flex items-center gap-1 text-[10px] text-cyan-700 font-semibold hover:underline">
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? 'Show less' : `Show all ${data.students.length} students`}
        </button>
      )}
    </div>
  );
}

/* ─────────── StructuredData renderer ───────────────────────────────── */
export default function StructuredData({ structuredData }) {
  if (!structuredData) return null;
  const cards = [
    [PendingStudentsCard, structuredData.pending_students],
    [GradeStudentsCard, structuredData.grade_students],
    [StudentProfileCard, structuredData.profile],
    [FeeSummaryCard, structuredData.fees],
    [ResultsCard, structuredData.results],
    [StudentRiskCard, structuredData.student_risk],
    [CollectionSummaryCard, structuredData.collection],
    [MonthlyCollectionCard, structuredData.monthly_collection],
    [StudentCountsCard, structuredData.student_counts],
    [TopStudentsCard, structuredData.top_students],
    [SubjectAveragesCard, structuredData.subject_averages],
    [AtRiskCard, structuredData.at_risk],
    [FindStudentsCard, structuredData.students],
  ];
  return (
    <>
      {cards.map(([Card, data], index) => (data ? <Card key={index} data={data} /> : null))}
    </>
  );
}
