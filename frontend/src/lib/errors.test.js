import test from 'node:test';
import assert from 'node:assert/strict';
import { apiErrorMessage, SERVER_UNREACHABLE_MESSAGE } from './errors.js';

const withDetail = (detail) => ({ response: { data: { detail } } });

test('uses the message from the API when it is text', () => {
  assert.equal(apiErrorMessage(withDetail('Too many failed attempts.'), 'fallback'), 'Too many failed attempts.');
});

test('turns a validation list into text, because React cannot render objects', () => {
  const error = withDetail([
    { loc: ['body', 'phone'], msg: 'Enter a valid phone number.', type: 'value_error' },
    { loc: ['body', 'name'], msg: 'Student name is too short.', type: 'value_error' },
  ]);

  assert.equal(apiErrorMessage(error, 'fallback'), 'Enter a valid phone number. Student name is too short.');
});

test('names the field when a built-in validation message does not', () => {
  const error = withDetail([{ loc: ['body', 'marks_obtained'], msg: 'Field required', type: 'missing' }]);

  assert.equal(apiErrorMessage(error, 'fallback'), 'marks obtained: Field required');
});

test('falls back when a validation list holds nothing readable', () => {
  assert.equal(apiErrorMessage(withDetail([{ loc: ['body'] }]), 'fallback'), 'fallback');
  assert.equal(apiErrorMessage(withDetail({ odd: true }), 'fallback'), 'fallback');
});

test('says the server is unreachable when there is no response', () => {
  assert.equal(apiErrorMessage(new Error('Network Error'), 'fallback'), SERVER_UNREACHABLE_MESSAGE);
});
