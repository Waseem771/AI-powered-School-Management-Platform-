import test from 'node:test';
import assert from 'node:assert/strict';
import { getStoredUser } from './session.js';

test('returns the stored user when the session data is valid', () => {
  const storage = {
    getItem: () => '{"username":"admin","role":"admin"}',
  };

  assert.deepEqual(getStoredUser(storage), { username: 'admin', role: 'admin' });
});

test('falls back to an administrator profile when session data is missing or malformed', () => {
  assert.deepEqual(getStoredUser({ getItem: () => null }), { username: 'admin', role: 'admin' });
  assert.deepEqual(getStoredUser({ getItem: () => 'not-json' }), { username: 'admin', role: 'admin' });
});
