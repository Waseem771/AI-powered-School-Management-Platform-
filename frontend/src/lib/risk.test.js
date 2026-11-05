import assert from 'node:assert/strict';
import test from 'node:test';

import {
  NOT_ENOUGH_DATA,
  bandCounts,
  bandLabel,
  explanationTitle,
  feeFollowUpText,
  scoreText,
  studentsInBand,
  trendText,
} from './risk.js';

test('a score is never written as a percentage', () => {
  assert.equal(scoreText(85), 'Score 85 of 100');
  assert.doesNotMatch(scoreText(85), /%/);
});

test('a student with no score says so', () => {
  assert.equal(scoreText(null), 'No score');
  assert.equal(bandLabel(NOT_ENOUGH_DATA), NOT_ENOUGH_DATA);
});

test('counts stay right whichever band is showing', () => {
  const students = [{ risk_category: 'High' }, { risk_category: 'High' }, { risk_category: 'Low' }, { risk_category: NOT_ENOUGH_DATA }];

  assert.deepEqual(bandCounts(students), { all: 4, High: 2, Medium: 0, Low: 1, [NOT_ENOUGH_DATA]: 1 });
  assert.equal(studentsInBand(students, 'High').length, 2);
  assert.equal(studentsInBand(students, 'all').length, 4);
});

test('fee follow-up appears only when needed', () => {
  assert.equal(feeFollowUpText({ needed: false, overdue_invoices: 0, overdue_amount: 0 }), null);
  assert.equal(feeFollowUpText(undefined), null);
  assert.match(feeFollowUpText({ needed: true, overdue_invoices: 1, overdue_amount: 3500 }), /1 overdue invoice, Rs 3,500/);
  assert.match(feeFollowUpText({ needed: true, overdue_invoices: 2, overdue_amount: 7000 }), /2 overdue invoices/);
});

test('no trend is shown as no trend', () => {
  assert.match(trendText({ grade_trend: null }), /No midterm and final/);
  assert.match(trendText({ grade_trend: -12.5 }), /Down 12.5 points/);
  assert.match(trendText({ grade_trend: 4 }), /Up 4 points/);
  assert.match(trendText({ grade_trend: 0 }), /No change/);
});

test('only real SHAP explanations are described as what moved the estimate', () => {
  assert.match(explanationTitle('shap'), /moved this estimate/);
  assert.doesNotMatch(explanationTitle('record'), /moved/);
});
