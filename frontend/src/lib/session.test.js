import test from 'node:test';
import assert from 'node:assert/strict';
import { clearSession, getStoredUser } from './session.js';

function fakeStorage(entries) {
  const data = new Map(Object.entries(entries));
  return {
    get length() {
      return data.size;
    },
    key: (index) => [...data.keys()][index] ?? null,
    getItem: (key) => data.get(key) ?? null,
    removeItem: (key) => data.delete(key),
    keys: () => [...data.keys()],
  };
}

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

test('clearing the session removes the token, user and chat history but nothing else', () => {
  const storage = fakeStorage({
    educore_token: 'token',
    educore_user: '{}',
    educore_chat_history: '[]',
    educore_chat_session_id: 'abc',
    unrelated_setting: 'keep',
  });

  clearSession(storage);

  assert.deepEqual(storage.keys(), ['unrelated_setting']);
});
