import assert from 'node:assert/strict';
import test from 'node:test';

import { activityText, formatDate } from './activity.js';
import { answerSource, policyName } from './chatStatus.js';
import { entriesToSave, markProblems, markText, startingTotal, totalProblem } from './classMarks.js';

test('activity lines say what happened', () => {
  assert.equal(activityText({ kind: 'payment', amount: 1500, month: 'October 2026' }), 'Rs. 1,500 received for October 2026');
  assert.equal(activityText({ kind: 'challan', amount: 4000, month: 'October 2026' }), 'Rs. 4,000 challan issued for October 2026');
  assert.equal(activityText({ kind: 'enrolment', class_name: 'Grade 8-A' }), 'Enrolled in Grade 8-A');
});

test('dates read clearly, and a missing one says so', () => {
  assert.equal(formatDate('2026-11-05T10:00:00+00:00'), '5 Nov 2026');
  assert.equal(formatDate(null), 'Not recorded');
  assert.equal(formatDate('not a date'), 'Not recorded');
});

test('each chatbot answer says where it came from', () => {
  assert.equal(answerSource({ mode: 'school_data', grounded: true }), 'From school records');
  assert.equal(answerSource({ mode: 'groq_tool_calling', grounded: true }), 'From school records, worded by AI');
  assert.equal(answerSource({ mode: 'policy_rag', grounded: true }), 'From policy documents');
  assert.equal(answerSource({ mode: 'policy_rag', grounded: false }), null);
  assert.equal(answerSource({}), null);
});

test('policy files get plain names', () => {
  assert.equal(policyName('fee_policy.txt'), 'Fee policy');
  assert.equal(policyName('academic_calendar.txt'), 'Academic calendar');
});

test('a class sheet starts from what is saved', () => {
  assert.equal(markText(null), '');
  assert.equal(markText(0), '0');
  assert.equal(startingTotal([{ total_marks: null }, { total_marks: 75 }]), 75);
  assert.equal(startingTotal([{ total_marks: null }]), 100);
});

test('a class sheet flags only the marks that are wrong', () => {
  const rows = [
    { id: 1, mark: '' },
    { id: 2, mark: '45' },
    { id: 3, mark: '120' },
    { id: 4, mark: 'abc' },
    { id: 5, mark: '-1' },
    { id: 6, mark: '0' },
  ];

  assert.deepEqual(Object.keys(markProblems(rows, '100')), ['3', '4', '5']);
  assert.match(markProblems(rows, '100')[3], /more than the total/i);
});

test('total marks must make sense', () => {
  assert.equal(totalProblem('100'), '');
  assert.match(totalProblem(''), /greater than zero/);
  assert.match(totalProblem('0'), /greater than zero/);
  assert.match(totalProblem('5000'), /1000/);
});

test('blank boxes are never sent, and zero is', () => {
  const rows = [{ id: 1, mark: '' }, { id: 2, mark: ' 45.5 ' }, { id: 3, mark: '0' }];

  assert.deepEqual(entriesToSave(rows), [
    { student_id: 2, marks_obtained: 45.5 },
    { student_id: 3, marks_obtained: 0 },
  ]);
});
