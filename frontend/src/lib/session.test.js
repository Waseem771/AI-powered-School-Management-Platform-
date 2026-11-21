import test from 'node:test';
import assert from 'node:assert/strict';
import { clearSession, getStoredUser, mustChangePassword, setPasswordChangeRequired } from './session.js';

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

function writableStorage(initial) {
  const data = new Map(Object.entries(initial));
  return { getItem: (key) => data.get(key) ?? null, setItem: (key, value) => data.set(key, value), read: (key) => data.get(key) };
}

test('a required password change is remembered, kept apart from the rest of the user, and cleared once done', () => {
  const storage = writableStorage({ educore_user: '{"username":"mr.khan","role":"parent"}' });

  assert.equal(mustChangePassword(getStoredUser(storage)), false);
  setPasswordChangeRequired(true, storage);
  assert.deepEqual(JSON.parse(storage.read('educore_user')), { username: 'mr.khan', role: 'parent', must_change_password: true });
  assert.equal(mustChangePassword(getStoredUser(storage)), true);

  setPasswordChangeRequired(false, storage);
  assert.deepEqual(JSON.parse(storage.read('educore_user')), { username: 'mr.khan', role: 'parent' });
  assert.equal(mustChangePassword(getStoredUser(storage)), false);
});

test('only an explicit true counts as a required change', () => {
  for (const value of [undefined, null, false, 'true', 1]) {
    assert.equal(mustChangePassword({ must_change_password: value }), false);
  }
  assert.equal(mustChangePassword(null), false);
});
