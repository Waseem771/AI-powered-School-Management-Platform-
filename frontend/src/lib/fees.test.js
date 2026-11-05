import test from 'node:test';
import assert from 'node:assert/strict';
import { challanFormError, defaultDueDate, monthLabel, monthPickerValue, paymentAmountError } from './fees.js';

test('month picker value comes from the current date, not a fixed month', () => {
  assert.equal(monthPickerValue(new Date(2026, 0, 15)), '2026-01');
  assert.equal(monthPickerValue(new Date(2026, 10, 5)), '2026-11');
});

test('month labels use the format the API expects', () => {
  assert.equal(monthLabel('2026-11'), 'November 2026');
  assert.equal(monthLabel('2027-01'), 'January 2027');
});

test('due date defaults to the 10th of the billing month', () => {
  assert.equal(defaultDueDate('2026-11'), '2026-11-10');
});

test('challan form needs a month, a due date and a positive amount', () => {
  const valid = { amount: '4000', month: '2026-11', due_date: '2026-11-10' };

  assert.equal(challanFormError(valid), null);
  assert.ok(challanFormError({ ...valid, month: '' }));
  assert.ok(challanFormError({ ...valid, due_date: '' }));
  assert.ok(challanFormError({ ...valid, amount: '0' }));
  assert.ok(challanFormError({ ...valid, amount: '-5' }));
  assert.ok(challanFormError({ ...valid, amount: '' }));
});

test('payment must be above zero and no more than the balance', () => {
  assert.equal(paymentAmountError('1500', 4000), null);
  assert.equal(paymentAmountError('4000', 4000), null);
  assert.ok(paymentAmountError('', 4000));
  assert.ok(paymentAmountError('0', 4000));
  assert.ok(paymentAmountError('-1', 4000));
  assert.match(paymentAmountError('4000.01', 4000), /more than/);
});
