import assert from 'node:assert/strict';
import test from 'node:test';

import {
  canGoForward,
  classText,
  examFromValue,
  examValue,
  feeLine,
  feeTone,
  latestResultLine,
  paymentHistory,
  pickChild,
  rateLine,
  rateTone,
  shiftMonth,
  weekdayOf,
} from './parent.js';

const children = [{ id: 4, name: 'Ayesha' }, { id: 9, name: 'Hamza' }];

test('the child in the address is chosen, and a child the parent does not have is never chosen', () => {
  assert.equal(pickChild(children, '9').name, 'Hamza');
  assert.equal(pickChild(children, 9).name, 'Hamza');
  assert.equal(pickChild(children, '77').name, 'Ayesha');
  assert.equal(pickChild(children, undefined).name, 'Ayesha');
  assert.equal(pickChild([], '4'), null);
  assert.equal(pickChild(null, '4'), null);
});

test('class and month wording', () => {
  assert.equal(classText({ grade: 'Grade 8', section: 'B' }), 'Grade 8-B');
  assert.equal(shiftMonth('2026-11', -1), '2026-10');
  assert.equal(shiftMonth('2026-01', -1), '2025-12');
  assert.equal(shiftMonth('2026-12', 1), '2027-01');
  assert.equal(weekdayOf('2026-11-20'), 'Friday');
  assert.equal(weekdayOf('nonsense'), '');
});

test('a parent cannot page forward past the current month', () => {
  assert.equal(canGoForward('2026-10', '2026-11-20'), true);
  assert.equal(canGoForward('2026-11', '2026-11-20'), false);
});

test('attendance says so plainly when nothing is recorded, and never shows 0%', () => {
  assert.equal(rateLine({ attendance_rate: null }, 'this month'), 'No attendance recorded this month');
  assert.equal(rateLine(undefined, 'this month'), 'No attendance recorded this month');
  assert.equal(rateLine({ attendance_rate: 93.5 }, 'this month'), '93.5% this month');
  assert.equal(rateLine({ attendance_rate: 0 }, 'this session'), '0% this session');
  assert.equal(rateTone(null), 'neutral');
  assert.equal(rateTone(95), 'good');
  assert.equal(rateTone(80), 'warn');
  assert.equal(rateTone(60), 'bad');
});

test('the dashboard lines come from the real figures', () => {
  assert.equal(latestResultLine(null), 'No results released yet');
  assert.equal(latestResultLine({ percentage: 71.5, exam_type: 'Final Term', session: '2025-2026' }), '71.5% in Final Term (2025-2026)');
  assert.equal(feeLine({ invoice_count: 0, outstanding: 0 }), 'No fee challans yet');
  assert.equal(feeLine({ invoice_count: 2, outstanding: 0 }), 'All fees paid');
  assert.equal(feeLine({ invoice_count: 2, outstanding: 6500 }), 'Rs. 6,500 to pay');
  assert.equal(feeTone({ invoice_count: 2, outstanding: 6500, overdue: 4000 }), 'bad');
  assert.equal(feeTone({ invoice_count: 2, outstanding: 6500, overdue: 0 }), 'warn');
  assert.equal(feeTone({ invoice_count: 2, outstanding: 0, overdue: 0 }), 'good');
  assert.equal(feeTone({ invoice_count: 0, outstanding: 0, overdue: 0 }), 'neutral');
});

test('payment history is flattened across invoices, newest first', () => {
  const invoices = [
    { month: 'November 2026', challan_number: 'CHN-2', payments: [{ id: 7 }] },
    { month: 'October 2026', challan_number: 'CHN-1', payments: [{ id: 3 }, { id: 9 }] },
    { month: 'September 2026', challan_number: 'CHN-0', payments: [] },
  ];

  assert.deepEqual(paymentHistory(invoices).map((payment) => [payment.id, payment.month]), [
    [9, 'October 2026'], [7, 'November 2026'], [3, 'October 2026'],
  ]);
  assert.deepEqual(paymentHistory(undefined), []);
});

test('an exam survives a round trip through the picker', () => {
  const exam = { academic_year_id: 2, exam_type: 'Final Term' };
  assert.equal(examValue(exam), '2|Final Term');
  assert.deepEqual(examFromValue('2|Final Term'), exam);
});
