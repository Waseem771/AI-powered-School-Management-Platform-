/** Wording and small rules for the Parent Portal. Display only: the server decides what a parent may see. */
import { monthLabel } from './fees.js';

const RELATIONSHIPS = ['Father', 'Mother', 'Guardian'];
export const RELATIONSHIP_OPTIONS = [
  { value: '', label: 'Not stated' },
  ...RELATIONSHIPS.map((name) => ({ value: name, label: name })),
];

/** The child named in the address (?child=3), or the first one. Never a child the parent does not have. */
export function pickChild(children, childParam) {
  if (!children?.length) return null;
  return children.find((child) => String(child.id) === String(childParam)) ?? children[0];
}

/** "Grade 8-B". */
export function classText(child) {
  return `${child.grade}-${child.section}`;
}

/** "2026-11" moved by whole months. */
export function shiftMonth(month, delta) {
  const [year, number] = month.split('-').map(Number);
  const moved = new Date(Date.UTC(year, number - 1 + delta, 1));
  return `${moved.getUTCFullYear()}-${String(moved.getUTCMonth() + 1).padStart(2, '0')}`;
}

export function monthTitle(month) {
  return month ? monthLabel(month) : '';
}

/** A parent may look back freely but not forward past the school's today. */
export function canGoForward(month, today) {
  return month < today.slice(0, 7);
}

/** "Mon" for an ISO date. */
export function weekdayOf(iso) {
  const date = new Date(`${iso}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString('en-GB', { weekday: 'long', timeZone: 'UTC' });
}

/** One line for a card: "93.5% this month", or a plain statement when nothing was recorded. Never 0% for no data. */
export function rateLine(summary, label) {
  if (!summary || summary.attendance_rate === null || summary.attendance_rate === undefined) {
    return `No attendance recorded ${label}`;
  }
  return `${summary.attendance_rate}% ${label}`;
}

/** Green from 90%, amber from 75%, otherwise red, and neutral when there is nothing to judge. */
export function rateTone(rate) {
  if (rate === null || rate === undefined) return 'neutral';
  if (rate >= 90) return 'good';
  if (rate >= 75) return 'warn';
  return 'bad';
}

/** "Final Term (2025-2026)" with the percentage, for the card on the dashboard. */
export function latestResultLine(result) {
  if (!result) return 'No results released yet';
  const session = result.session ? ` (${result.session})` : '';
  return `${result.percentage}% in ${result.exam_type}${session}`;
}

/** What the money cards say. Fully paid reads as such rather than as "Rs. 0". */
export function feeLine(fees) {
  if (!fees || fees.invoice_count === 0) return 'No fee challans yet';
  if (fees.outstanding === 0) return 'All fees paid';
  return `Rs. ${fees.outstanding.toLocaleString()} to pay`;
}

export function feeTone(fees) {
  if (!fees || fees.invoice_count === 0) return 'neutral';
  if (fees.overdue > 0) return 'bad';
  return fees.outstanding > 0 ? 'warn' : 'good';
}

export function paymentModeLabel(mode) {
  return { cash: 'Cash', bank: 'Bank', online: 'Online' }[mode] ?? (mode ? mode.charAt(0).toUpperCase() + mode.slice(1) : '');
}

/** Payments across all of a child's invoices, newest first, each with the month it was for. */
export function paymentHistory(invoices) {
  return (invoices ?? [])
    .flatMap((invoice) => invoice.payments.map((payment) => ({ ...payment, month: invoice.month, challan_number: invoice.challan_number })))
    .sort((a, b) => b.id - a.id);
}

/** The option value of an exam in a picker, and the query that asks for exactly it. */
export function examValue(exam) {
  return `${exam.academic_year_id}|${exam.exam_type}`;
}

export function examFromValue(value) {
  const [year, ...type] = String(value).split('|');
  return { academic_year_id: Number(year), exam_type: type.join('|') };
}
