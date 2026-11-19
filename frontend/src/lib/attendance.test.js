import assert from 'node:assert/strict';
import test from 'node:test';

import {
  classLabel, correctionCount, entriesFrom, marksFrom, monthRange, rateText, savingProblem, schoolToday, shiftDate,
  stateInfo, statusLabel, tally, unmarkedStudents,
} from './attendance.js';

const students = [
  { id: 1, name: 'A', status: null },
  { id: 2, name: 'B', status: 'absent' },
  { id: 3, name: 'C', status: null },
];

test('classes and states read plainly', () => {
  assert.equal(classLabel('Grade 8', 'A'), 'Grade 8-A');
  assert.equal(statusLabel('late'), 'Late');
  assert.equal(statusLabel(null), 'Not recorded');
  assert.equal(stateInfo('not_submitted').label, 'Not submitted');
  assert.equal(stateInfo('complete').label, 'Submitted');
  assert.equal(stateInfo('nonsense').label, 'Not submitted');
});

test('no records is never shown as 0%', () => {
  assert.equal(rateText(null), 'No records');
  assert.equal(rateText(0), '0%');
  assert.equal(rateText(93.5), '93.5%');
});

test('the sheet starts from what is saved, and unsaved students stay unmarked', () => {
  const marks = marksFrom(students);

  assert.deepEqual(marks, { 2: 'absent' });
  assert.deepEqual(unmarkedStudents(students, marks).map((s) => s.id), [1, 3]);
  assert.deepEqual(tally(students, marks), { present: 0, absent: 1, late: 0, leave: 0, unmarked: 2 });
});

test('saving needs every student marked, and a reason only for corrections', () => {
  assert.equal(savingProblem(students, { 2: 'absent' }, ''), '2 students are not marked yet.');
  assert.equal(savingProblem(students, { 1: 'present', 2: 'absent' }, ''), '1 student is not marked yet.');
  assert.equal(savingProblem(students, { 1: 'present', 2: 'absent', 3: 'late' }, ''), '');
  assert.equal(correctionCount(students, { 1: 'present', 2: 'present', 3: 'late' }), 1);
  assert.equal(
    savingProblem(students, { 1: 'present', 2: 'present', 3: 'late' }, '  '),
    'Say why you are correcting saved attendance.',
  );
  assert.equal(savingProblem(students, { 1: 'present', 2: 'present', 3: 'late' }, 'Parent called'), '');
  assert.equal(savingProblem([], {}, ''), 'This class has no students.');
});

test('a partial save is possible for administrators, but never an empty one', () => {
  assert.equal(savingProblem(students, {}, '', false), 'Mark at least one student.');
  assert.equal(savingProblem(students, { 1: 'present' }, '', false), '');
});

test('only marked students are sent', () => {
  assert.deepEqual(entriesFrom(students, { 1: 'present', 3: 'late' }), [
    { student_id: 1, status: 'present' }, { student_id: 3, status: 'late' },
  ]);
});

test('a month runs from its first to its last day, including leap years', () => {
  assert.deepEqual(monthRange('2026-02'), { start: '2026-02-01', end: '2026-02-28' });
  assert.deepEqual(monthRange('2028-02'), { start: '2028-02-01', end: '2028-02-29' });
  assert.deepEqual(monthRange('2026-11'), { start: '2026-11-01', end: '2026-11-30' });
  assert.deepEqual(monthRange('2026-12'), { start: '2026-12-01', end: '2026-12-31' });
});

test('dates move across month ends and use school time', () => {
  assert.equal(shiftDate('2026-03-01', -1), '2026-02-28');
  assert.equal(shiftDate('2026-12-31', 1), '2027-01-01');
  // 20:00 UTC is already the next day in Pakistan.
  assert.equal(schoolToday(Date.UTC(2026, 10, 19, 20, 0)), '2026-11-20');
  assert.equal(schoolToday(Date.UTC(2026, 10, 19, 10, 0)), '2026-11-19');
});
