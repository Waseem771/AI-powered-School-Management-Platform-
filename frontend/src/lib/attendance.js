/** Attendance wording and rules shared by the teacher and administrator screens. */
export const STATUS_OPTIONS = [
  { value: 'present', label: 'Present', tone: 'good' },
  { value: 'absent', label: 'Absent', tone: 'bad' },
  { value: 'late', label: 'Late', tone: 'warn' },
  { value: 'leave', label: 'Leave', tone: 'info' },
];

const STATE_TEXT = {
  not_submitted: { label: 'Not submitted', tone: 'warn' },
  partial: { label: 'Partly submitted', tone: 'info' },
  complete: { label: 'Submitted', tone: 'good' },
};

export const REASON_MIN_LENGTH = 3;

export function classLabel(grade, section) {
  return `${grade}-${section}`;
}

export function statusLabel(status) {
  return STATUS_OPTIONS.find((option) => option.value === status)?.label ?? 'Not recorded';
}

export function statusTone(status) {
  return STATUS_OPTIONS.find((option) => option.value === status)?.tone ?? 'neutral';
}

export function stateInfo(state) {
  return STATE_TEXT[state] ?? STATE_TEXT.not_submitted;
}

/** "93.5%", or a plain statement when nothing has been recorded. Never 0% for no data. */
export function rateText(rate) {
  return rate === null || rate === undefined ? 'No records' : `${rate}%`;
}

/** The marks map starts from what is already saved: { studentId: status }. */
export function marksFrom(students) {
  return Object.fromEntries(students.filter((student) => student.status).map((student) => [student.id, student.status]));
}

export function unmarkedStudents(students, marks) {
  return students.filter((student) => !marks[student.id]);
}

/** Existing records whose status has been changed. They are corrections and need a reason. */
export function correctionCount(students, marks) {
  return students.filter((student) => student.status && marks[student.id] && marks[student.id] !== student.status).length;
}

/** The first problem that stops saving, or '' when it can be saved. */
export function savingProblem(students, marks, reason, requireAll = true) {
  if (students.length === 0) return 'This class has no students.';
  const left = unmarkedStudents(students, marks).length;
  if (requireAll && left > 0) return `${left} ${left === 1 ? 'student is' : 'students are'} not marked yet.`;
  if (!requireAll && Object.keys(marks).length === 0) return 'Mark at least one student.';
  if (correctionCount(students, marks) > 0 && (reason ?? '').trim().length < REASON_MIN_LENGTH) {
    return 'Say why you are correcting saved attendance.';
  }
  return '';
}

export function entriesFrom(students, marks) {
  return students.filter((student) => marks[student.id]).map((student) => ({ student_id: student.id, status: marks[student.id] }));
}

export function tally(students, marks) {
  const counts = { present: 0, absent: 0, late: 0, leave: 0, unmarked: 0 };
  students.forEach((student) => {
    const status = marks[student.id];
    if (status) counts[status] += 1;
    else counts.unmarked += 1;
  });
  return counts;
}

export function shiftDate(iso, days) {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

/** The date at the school (Pakistan time), used only until the server says what today is. */
export function schoolToday(now = Date.now()) {
  return new Date(now + 5 * 3600 * 1000).toISOString().slice(0, 10);
}

export function longDate(iso) {
  const date = new Date(`${iso}T00:00:00Z`);
  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
}

export function monthOf(iso) {
  return iso.slice(0, 7);
}

/** The first and last day of a "YYYY-MM" month. */
export function monthRange(month) {
  const [year, number] = month.split('-').map(Number);
  return { start: `${month}-01`, end: new Date(Date.UTC(year, number, 0)).toISOString().slice(0, 10) };
}
