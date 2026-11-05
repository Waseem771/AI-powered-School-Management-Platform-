import assert from 'node:assert/strict';
import test from 'node:test';

import { chatStatusSummary, describeChatStatus } from './chatStatus.js';

const labels = (status) => describeChatStatus(status).map((line) => line.label).join(' | ');

test('claims nothing before the server has answered', () => {
  assert.equal(describeChatStatus(null).length, 1);
  assert.equal(describeChatStatus(null)[0].tone, 'off');
  assert.doesNotMatch(chatStatusSummary(null), /AI/);
});

test('says the language model is off when there is no key', () => {
  const status = { language_model: { configured: false, last_call_ok: null }, policy_search: { engine: 'tfidf' } };
  assert.match(labels(status), /language model: off/);
  assert.match(labels(status), /keyword-based/);
  assert.doesNotMatch(chatStatusSummary(status), /AI/);
});

test('does not say the model works until a call has worked', () => {
  const status = { language_model: { configured: true, last_call_ok: null }, policy_search: { engine: 'not_loaded' } };
  assert.match(labels(status), /not used yet/);
});

test('reports a failed call', () => {
  const status = { language_model: { configured: true, last_call_ok: false }, policy_search: { engine: 'faiss' } };
  assert.match(labels(status), /last call failed/);
  assert.equal(describeChatStatus(status)[0].tone, 'warn');
  assert.doesNotMatch(chatStatusSummary(status), /AI/);
});

test('says the model is on after a call worked', () => {
  const status = { language_model: { configured: true, last_call_ok: true }, policy_search: { engine: 'faiss' } };
  assert.match(labels(status), /language model: on/);
  assert.match(chatStatusSummary(status), /AI/);
});
