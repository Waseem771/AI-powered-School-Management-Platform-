// Rules for the admissions screens. The server checks everything again; these only save a round trip.

export const STATUS_TONES = {
  new: 'info',
  under_review: 'warn',
  test_interview: 'warn',
  approved: 'good',
  rejected: 'bad',
  enrolled: 'good',
};

export const EMPTY_APPLICATION = {
  student_name: '',
  dob: '',
  gender: '',
  applying_grade: '',
  previous_class: '',
  previous_school: '',
  previous_performance: '',
  guardian_name: '',
  guardian_relationship: 'Father',
  phone: '',
  alt_phone: '',
  address: '',
  staff_notes: '',
};

const OPTIONAL_TEXT = ['gender', 'previous_class', 'previous_school', 'previous_performance', 'alt_phone', 'staff_notes'];
const PHONE_DIGITS = [10, 15];
const MIN_AGE = 3;
const MAX_AGE = 30;

const digitCount = (value) => [...value].filter((character) => character >= '0' && character <= '9').length;
const isPhone = (value) => /^\+?[0-9][0-9 ()-]*$/.test(value) && digitCount(value) >= PHONE_DIGITS[0] && digitCount(value) <= PHONE_DIGITS[1];
const isPersonName = (value) => /^[\p{L}\p{M} .'-]{2,100}$/u.test(value);

function ageProblem(dob, today) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dob) || Number.isNaN(Date.parse(dob))) return 'Enter a real date of birth.';
  const age = today.getFullYear() - Number(dob.slice(0, 4));
  if (age < MIN_AGE || age > MAX_AGE) return `Date of birth must make the student ${MIN_AGE} to ${MAX_AGE} years old.`;
  return '';
}

/** A message for each field that is wrong, keyed by field name. Empty means the form can be sent. */
export function applicationProblems(form, today = new Date()) {
  const problems = {};
  const text = (name) => (form[name] || '').trim();

  if (!isPersonName(text('student_name'))) problems.student_name = "Enter the student's full name, using letters only.";
  const dobProblem = text('dob') ? ageProblem(text('dob'), today) : 'Enter the date of birth.';
  if (dobProblem) problems.dob = dobProblem;
  if (!text('applying_grade')) problems.applying_grade = 'Choose the class applied for.';
  if (!isPersonName(text('guardian_name'))) problems.guardian_name = "Enter the guardian's full name, using letters only.";
  if (!isPhone(text('phone'))) problems.phone = 'Enter a phone number, such as 0300-1234567.';
  if (text('alt_phone') && !isPhone(text('alt_phone'))) problems.alt_phone = 'Enter a phone number, such as 0300-1234567, or leave this blank.';
  if (text('address').length < 5) problems.address = 'Enter the home address.';
  return problems;
}

/** What goes to the server: trimmed text, and blank optional fields as null. */
export function applicationPayload(form) {
  const payload = {};
  Object.entries(form).forEach(([name, value]) => {
    const trimmed = typeof value === 'string' ? value.trim() : value;
    payload[name] = OPTIONAL_TEXT.includes(name) && trimmed === '' ? null : trimmed;
  });
  return payload;
}

export function testPercentage(obtained, maximum) {
  const marks = Number(obtained);
  const total = Number(maximum);
  if (!Number.isFinite(marks) || !Number.isFinite(total) || total <= 0) return null;
  return Math.round((marks / total) * 1000) / 10;
}

export function assessmentProblems(form) {
  const problems = {};
  const maximum = Number(form.max_marks);
  const obtained = Number(form.obtained_marks);
  if (!form.test_date) problems.test_date = 'Choose the test date.';
  if ((form.subject || '').trim().length < 2) problems.subject = 'Enter the subject or assessment name.';
  if (form.max_marks === '' || !(maximum > 0)) problems.max_marks = 'Enter the maximum marks.';
  if (form.obtained_marks === '' || !(obtained >= 0)) problems.obtained_marks = 'Enter the marks obtained.';
  else if (maximum > 0 && obtained > maximum) problems.obtained_marks = 'Marks obtained cannot be more than the maximum.';
  return problems;
}

/** The wording of the confirmation shown before a status changes. */
export function statusConfirmation(toStatus, label) {
  if (toStatus === 'approved') return { title: 'Approve this application?', body: 'The applicant can then be enrolled as a student.', needsNote: false, confirm: 'Approve' };
  if (toStatus === 'rejected') return { title: 'Reject this application?', body: 'It stays in the list as a record. Please give the reason.', needsNote: true, confirm: 'Reject' };
  return { title: `Move to "${label}"?`, body: 'The change is recorded in the history.', needsNote: false, confirm: 'Move' };
}

export function isoToday(now = new Date()) {
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}
