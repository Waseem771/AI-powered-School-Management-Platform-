import React from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Printer } from 'lucide-react';
import { api } from '../api/client';
import Button from '../components/ui/Button';
import { ErrorState, LoadingState } from '../components/ui/States';
import { classLabel, longDate, rateText, schoolToday, shiftDate } from '../lib/attendance';
import { useLoad } from '../lib/useLoad';

const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** A plain page built to be printed (or saved as PDF from the print dialog). Tables only, from recorded attendance. */
export default function AttendanceReport() {
  const [params] = useSearchParams();
  const today = schoolToday();
  const end = DATE.test(params.get('end') ?? '') ? params.get('end') : today;
  const start = DATE.test(params.get('start') ?? '') ? params.get('start') : shiftDate(end, -29);
  const grade = params.get('grade') || undefined;
  const section = params.get('section') || undefined;

  const { data, loading, error, reload } = useLoad(
    (request) => api.getAttendanceReport({ start, end, grade, section }, request),
    `report-${start}-${end}-${grade}-${section}`,
    'Could not build the report. Please try again.',
  );

  if (loading) return <LoadingState label="Building the report…" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const scope = [grade, section && `Section ${section}`].filter(Boolean).join(', ') || 'All classes';

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link to="/attendance" className="inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold text-brand-700 hover:underline">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Attendance
        </Link>
        <Button onClick={() => window.print()}><Printer className="h-4 w-4" aria-hidden="true" /><span>Print report</span></Button>
      </div>

      <article className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 print:border-0 print:p-0">
        <header>
          <h1 className="text-2xl font-bold text-navy-900">Attendance Report</h1>
          <p className="text-sm text-slate-700">{scope} · {longDate(data.first)} to {longDate(data.last)}</p>
          <p className="text-xs text-slate-600">Prepared on {longDate(data.generated_on)}. Counts come only from attendance teachers recorded. Days or classes with no record are not counted as absent.</p>
        </header>

        <section aria-labelledby="totals-heading">
          <h2 id="totals-heading" className="mb-2 text-base font-bold text-slate-900">Whole period</h2>
          <dl className="grid grid-cols-3 gap-3 text-sm sm:grid-cols-6">
            {[['Records', data.totals.recorded], ['Present', data.totals.present], ['Absent', data.totals.absent], ['Late', data.totals.late], ['Leave', data.totals.leave], ['Attendance', rateText(data.totals.attendance_rate)]].map(([label, value]) => (
              <div key={label}><dt className="text-xs text-slate-600">{label}</dt><dd className="text-lg font-bold text-slate-900">{value}</dd></div>
            ))}
          </dl>
        </section>

        <section aria-labelledby="classes-heading">
          <h2 id="classes-heading" className="mb-2 text-base font-bold text-slate-900">By class</h2>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-slate-300 text-xs text-slate-700">
                  {['Class', 'Students', 'Days recorded', 'Present', 'Absent', 'Late', 'Leave', 'Attendance'].map((h, i) => <th key={h} scope="col" className={`px-2 py-2 ${i ? 'text-right' : ''}`}>{h}</th>)}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.classes.map((row) => (
                  <tr key={classLabel(row.grade, row.section)}>
                    <th scope="row" className="px-2 py-1.5 font-semibold">{classLabel(row.grade, row.section)}</th>
                    {[row.enrolled, row.days_recorded, row.present, row.absent, row.late, row.leave, rateText(row.attendance_rate)].map((value, i) => <td key={i} className="px-2 py-1.5 text-right">{value}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section aria-labelledby="absent-heading">
          <h2 id="absent-heading" className="mb-2 text-base font-bold text-slate-900">Students with 3 or more recorded absences</h2>
          {data.frequent_absentees.length === 0 ? (
            <p className="text-sm text-slate-600">No student reached 3 recorded absences in this period.</p>
          ) : (
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-slate-300 text-xs text-slate-700">
                  {['Student', 'Class', 'Absences', 'Days recorded', 'Absence rate'].map((h, i) => <th key={h} scope="col" className={`px-2 py-2 ${i > 1 ? 'text-right' : ''}`}>{h}</th>)}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.frequent_absentees.map((s) => (
                  <tr key={s.id}>
                    <td className="px-2 py-1.5">{s.name} <span className="text-xs text-slate-600">(Roll no. {s.roll_number})</span></td>
                    <td className="px-2 py-1.5">{classLabel(s.grade, s.section)}</td>
                    <td className="px-2 py-1.5 text-right">{s.absent}</td>
                    <td className="px-2 py-1.5 text-right">{s.days_recorded}</td>
                    <td className="px-2 py-1.5 text-right">{s.absence_rate}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </article>
    </div>
  );
}
