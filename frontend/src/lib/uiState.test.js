import assert from 'node:assert/strict';
import test from 'node:test';

import { addToast, countLabel, focusTrapTarget, nextActiveIndex, studentLabel, viewState } from './uiState.js';

test('a failure never looks like an empty list', () => {
  assert.equal(viewState({ loading: false, error: 'Server down', count: 0 }), 'error');
  assert.equal(viewState({ loading: false, error: '', count: 0 }), 'empty');
  assert.equal(viewState({ loading: true, error: 'Old error', count: 0 }), 'loading');
  assert.equal(viewState({ loading: false, error: '', count: 3 }), 'ready');
});

test('list highlight wraps at both ends', () => {
  assert.equal(nextActiveIndex(-1, 1, 3), 0);
  assert.equal(nextActiveIndex(-1, -1, 3), 2);
  assert.equal(nextActiveIndex(2, 1, 3), 0);
  assert.equal(nextActiveIndex(0, -1, 3), 2);
  assert.equal(nextActiveIndex(0, 1, 0), -1);
});

test('tab stays inside a dialog', () => {
  const [first, middle, last] = ['first', 'middle', 'last'];
  const focusable = [first, middle, last];

  assert.equal(focusTrapTarget(focusable, last, false), first);
  assert.equal(focusTrapTarget(focusable, first, true), last);
  assert.equal(focusTrapTarget(focusable, middle, false), null);
  assert.equal(focusTrapTarget([], null, false), null);
});

test('a student is named with roll number and class, so two with one name differ', () => {
  const label = studentLabel({ name: 'Ahmed Khan', roll_number: '045', grade: 'Grade 8', section: 'B' });

  assert.equal(label, 'Ahmed Khan (#045, Grade 8-B)');
});

test('counts read correctly', () => {
  assert.equal(countLabel(1, 'student'), '1 student');
  assert.equal(countLabel(5, 'student'), '5 students');
});

test('toasts keep only the latest few, without changing the old list', () => {
  const start = [];
  const one = addToast(start, 'success', 'a');
  const many = addToast(addToast(addToast(one, 'success', 'b'), 'success', 'c'), 'error', 'd');

  assert.deepEqual(start, []);
  assert.deepEqual(many.map((toast) => toast.message), ['b', 'c', 'd']);
  assert.equal(new Set(many.map((toast) => toast.id)).size, 3);
});
