import React from 'react';
import { STATUS_OPTIONS, tally } from '../lib/attendance';

const ACTIVE = {
  present: 'border-emerald-700 bg-emerald-700 text-white',
  absent: 'border-rose-700 bg-rose-700 text-white',
  late: 'border-amber-600 bg-amber-500 text-slate-900',
  leave: 'border-brand-700 bg-brand-700 text-white',
};
const IDLE = 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50';

export function TallyBar({ students, marks }) {
  const counts = tally(students, marks);
  const items = [...STATUS_OPTIONS.map((option) => [option.label, counts[option.value]]), ['Not marked', counts.unmarked]];
  return (
    <dl className="flex flex-wrap gap-x-5 gap-y-1 text-sm" aria-live="polite">
      {items.map(([label, value]) => (
        <div key={label} className="flex items-baseline gap-1.5">
          <dt className="text-slate-600">{label}</dt>
          <dd className="font-bold text-slate-900">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * One row per student with four big buttons, so a class of 30 to 50 can be marked quickly, by tap or keyboard.
 * `marks` is { studentId: status }. A student with no mark is simply not marked, never absent.
 */
export default function AttendanceSheet({ students, marks, onMark, disabled = false }) {
  return (
    <ul className="divide-y divide-slate-100">
      {students.map((student) => (
        <li key={student.id} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">{student.name}</p>
            <p className="text-xs text-slate-600">Roll no. {student.roll_number}</p>
          </div>
          <div role="radiogroup" aria-label={`Attendance for ${student.name}`} className="grid grid-cols-4 gap-1.5 sm:w-80">
            {STATUS_OPTIONS.map((option) => {
              const selected = marks[student.id] === option.value;
              return (
                <button
                  key={option.value}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  disabled={disabled}
                  onClick={() => onMark(student.id, option.value)}
                  className={`min-h-11 rounded-lg border px-1 text-xs font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60 sm:text-sm ${selected ? ACTIVE[option.value] : IDLE}`}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
        </li>
      ))}
    </ul>
  );
}

export function ChangeList({ changes }) {
  if (!changes?.length) return null;
  return (
    <section aria-labelledby="changes-heading" className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <h3 id="changes-heading" className="text-sm font-bold text-slate-900">Corrections made</h3>
      <ul className="mt-2 space-y-2 text-sm text-slate-700">
        {changes.map((change, index) => (
          <li key={`${change.student_id}-${change.changed_at}-${index}`}>
            <b>{change.student_name ?? 'Student'}</b>: {change.old_status} to {change.new_status}, by {change.changed_by ?? 'unknown'}.
            <span className="block text-xs text-slate-600">Reason: {change.reason}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
