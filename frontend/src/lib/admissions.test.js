import assert from 'node:assert/strict';
import test from 'node:test';

import {
  EMPTY_APPLICATION,
  applicationPayload,
  applicationProblems,
  assessmentProblems,
  statusConfirmation,
  testPercentage,
} from './admissions.js';

const today = new Date('2026-11-14T00:00:00Z');
const valid = {
  ...EMPTY_APPLICATION,
  student_name: 'Test Applicant',
  dob: '2013-05-10',
  applying_grade: 'Grade 7',
  guardian_name: 'Sample Guardian',
  phone: '0300-1112233',
  address: 'House 1, Test Street',
};

test('a complete application has no problems, and optional fields may stay blank', () => {
  assert.deepEqual(applicationProblems(valid, today), {});
});

test('each missing or wrong required field is named', () => {
  const problems = applicationProblems({ ...EMPTY_APPLICATION, phone: '123', student_name: 'X1' }, today);
  assert.deepEqual(Object.keys(problems).sort(), ['address', 'applying_grade', 'dob', 'guardian_name', 'phone', 'student_name']);
});

test('an optional phone is checked only when filled in', () => {
  assert.equal(applicationProblems({ ...valid, alt_phone: '' }, today).alt_phone, undefined);
  assert.ok(applicationProblems({ ...valid, alt_phone: 'abc' }, today).alt_phone);
});

test('an impossible age is refused', () => {
  assert.ok(applicationProblems({ ...valid, dob: '1980-01-01' }, today).dob);
  assert.ok(applicationProblems({ ...valid, dob: '2026-01-01' }, today).dob);
});

test('urdu names are accepted', () => {
  assert.equal(applicationProblems({ ...valid, student_name: 'احمد خان' }, today).student_name, undefined);
});

test('blank optional fields are sent as null and text is trimmed', () => {
  const payload = applicationPayload({ ...valid, student_name: '  Test Applicant ', previous_school: '  ' });
  assert.equal(payload.previous_school, null);
  assert.equal(payload.student_name, 'Test Applicant');
});

test('entry test percentages and problems', () => {
  assert.equal(testPercentage(31, 40), 77.5);
  assert.equal(testPercentage('x', 40), null);
  assert.equal(testPercentage(5, 0), null);
  const problems = assessmentProblems({ test_date: '2026-11-10', subject: 'English', max_marks: '40', obtained_marks: '41' });
  assert.ok(problems.obtained_marks);
  assert.deepEqual(assessmentProblems({ test_date: '2026-11-10', subject: 'English', max_marks: '40', obtained_marks: '0' }), {});
});

test('rejecting asks for a reason; approving does not', () => {
  assert.equal(statusConfirmation('rejected', 'Rejected').needsNote, true);
  assert.equal(statusConfirmation('approved', 'Approved').needsNote, false);
});
