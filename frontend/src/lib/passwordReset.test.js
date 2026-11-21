import test from 'node:test';
import assert from 'node:assert/strict';
import { looksLikeEmail, newPasswordProblem, readResetToken } from './passwordReset.js';

test('the token is read from the part after the #, with or without the #', () => {
  assert.equal(readResetToken('#token=abc_DEF-123'), 'abc_DEF-123');
  assert.equal(readResetToken('token=abc'), 'abc');
  assert.equal(readResetToken('#token= abc '), 'abc');
});

test('no token is found where there is none', () => {
  for (const value of ['', '#', '#other=1', '#token=', undefined, null]) {
    assert.equal(readResetToken(value), '');
  }
});

test('a new password must be long enough and typed twice the same', () => {
  assert.match(newPasswordProblem('short', 'short'), /at least 10/);
  assert.match(newPasswordProblem('', ''), /at least 10/);
  assert.match(newPasswordProblem('long-enough-1', 'different-1'), /do not match/);
  assert.equal(newPasswordProblem('long-enough-1', 'long-enough-1'), '');
});

test('exactly one valid email address is accepted', () => {
  for (const value of [' a@b.co ', 'First.Last@Example.COM', "o'brien+tag@sub.example.co.uk", 'x@y.pk']) {
    assert.equal(looksLikeEmail(value), true, value);
  }
});

test('lists, display names, header tricks and malformed addresses are refused', () => {
  const refused = [
    '', 'a', 'a@b', 'a@b.', 'a@.com', 'a..b@example.com', 'a b@example.com', 'a@@example.com', 'a@b@example.com',
    'a,b@example.com', 'a@example.com,b@example.com', 'a@example.com;b@example.com', 'a@example.com b@example.com',
    '<a@example.com>', 'Name <a@example.com>', '"a"@example.com', 'a@[127.0.0.1]', 'a@127.0.0.1', 'a\\b@example.com',
    'a@example.com\nBcc: x@y.com', 'a@example.com\r\nBcc: x@y.com', 'a@example.com\n', 'a\u0000@example.com',
    'é@example.com', 'a@-example.com', 'a@example.c', `${'x'.repeat(65)}@example.com`, null, undefined,
  ];
  for (const value of refused) assert.equal(looksLikeEmail(value), false, JSON.stringify(value));
});
