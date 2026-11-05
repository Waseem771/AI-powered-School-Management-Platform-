import test from 'node:test';
import assert from 'node:assert/strict';
import { examKey, examLabel, examParams, promotionBadge, promotionStyle } from './exams.js';
import { pdfErrorMessage } from './pdf.js';

const finalTerm = { exam_type: 'Final Term', academic_year_id: 1, session: '2025-2026' };

test('a badge only appears when the marks support a statement', () => {
  assert.equal(promotionBadge({ status: 'promoted' }), 'Promoted');
  assert.equal(promotionBadge({ status: 'not_promoted' }), 'Not promoted');
  assert.equal(promotionBadge({ status: 'incomplete' }), 'Not decided yet');
  assert.equal(promotionBadge({ status: 'not_applicable' }), null);
  assert.equal(promotionBadge({ status: 'no_marks' }), null);
  assert.equal(promotionBadge(undefined), null);
});

test('unknown statuses get the neutral style, never the green one', () => {
  assert.notEqual(promotionStyle('promoted'), promotionStyle('banana'));
  assert.equal(promotionStyle('banana'), promotionStyle(undefined));
});

test('exam labels include the session when it is known', () => {
  assert.equal(examLabel(finalTerm), 'Final Term (2025-2026)');
  assert.equal(examLabel({ exam_type: 'Midterm', academic_year_id: 9, session: null }), 'Midterm');
});

test('exam keys tell years apart', () => {
  assert.notEqual(examKey(finalTerm), examKey({ ...finalTerm, academic_year_id: 2 }));
});

test('exam params ask for one exam, or the latest when none is chosen', () => {
  assert.deepEqual(examParams(finalTerm), { exam_type: 'Final Term', academic_year_id: 1 });
  assert.deepEqual(examParams({ exam_type: 'Midterm' }), { exam_type: 'Midterm' });
  assert.deepEqual(examParams(null), {});
});

test('a PDF error reads the message out of the blob body', async () => {
  const body = new Blob([JSON.stringify({ detail: 'No marks recorded for this exam.' })]);

  assert.equal(await pdfErrorMessage({ response: { data: body } }), 'No marks recorded for this exam.');
});

test('a PDF error falls back when there is no readable message', async () => {
  const fallback = 'Could not open the PDF. Please try again.';

  assert.equal(await pdfErrorMessage(new Error('Network Error')), fallback);
  assert.equal(await pdfErrorMessage({ response: { data: new Blob(['not json']) } }), fallback);
  assert.equal(await pdfErrorMessage(null), fallback);
});
