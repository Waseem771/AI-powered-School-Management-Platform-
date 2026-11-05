import assert from 'node:assert/strict';
import test from 'node:test';

import { roleLabel, sessionLabel } from './schoolInfo.js';

test('the session comes from the server, or is left out', () => {
  assert.equal(sessionLabel({ academic_session: '2026-2027' }), 'Academic session 2026-2027');
  assert.equal(sessionLabel({ academic_session: null }), '');
  assert.equal(sessionLabel(null), '');
});

test('the role shows what the account holds', () => {
  assert.equal(roleLabel('admin'), 'Admin');
  assert.equal(roleLabel('accountant'), 'Accountant');
  assert.equal(roleLabel(undefined), '');
});
