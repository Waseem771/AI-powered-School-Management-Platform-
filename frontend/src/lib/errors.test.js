import test from 'node:test';
import assert from 'node:assert/strict';
import { apiErrorMessage, SERVER_UNREACHABLE_MESSAGE } from './errors.js';

test('uses the message from the API when it is text', () => {
  const error = { response: { data: { detail: 'Too many failed attempts.' } } };

  assert.equal(apiErrorMessage(error, 'fallback'), 'Too many failed attempts.');
});

test('never returns a validation error list, which React cannot render', () => {
  const error = { response: { data: { detail: [{ loc: ['body'], msg: 'too long' }] } } };

  assert.equal(apiErrorMessage(error, 'fallback'), 'fallback');
});

test('says the server is unreachable when there is no response', () => {
  assert.equal(apiErrorMessage(new Error('Network Error'), 'fallback'), SERVER_UNREACHABLE_MESSAGE);
});
