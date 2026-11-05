import test from 'node:test';
import assert from 'node:assert/strict';
import { openPdf } from './pdf.js';

function fakeBrowser(tab) {
  const calls = { openedBeforeFetch: false, downloaded: null, revoked: null, scheduled: null };
  return {
    calls,
    browser: {
      openTab: () => {
        calls.openedBeforeFetch = true;
        return tab;
      },
      createUrl: () => 'blob:pdf',
      revokeUrl: (url) => {
        calls.revoked = url;
      },
      download: (url) => {
        calls.downloaded = url;
      },
      schedule: (callback) => {
        calls.scheduled = callback;
      },
    },
  };
}

test('opens the tab before fetching, then shows the PDF in it', async () => {
  const tab = { location: {}, close() {} };
  const { browser, calls } = fakeBrowser(tab);

  const opened = await openPdf(async () => {
    assert.equal(calls.openedBeforeFetch, true);
    return 'blob';
  }, browser);

  assert.equal(opened, true);
  assert.equal(tab.location.href, 'blob:pdf');
});

test('downloads the PDF when the browser blocks the new tab', async () => {
  const { browser, calls } = fakeBrowser(null);

  assert.equal(await openPdf(async () => 'blob', browser), true);
  assert.equal(calls.downloaded, 'blob:pdf');
});

test('closes the empty tab and reports failure when the PDF cannot be loaded', async () => {
  let closed = false;
  const tab = { location: {}, close: () => (closed = true) };
  const { browser } = fakeBrowser(tab);

  const opened = await openPdf(async () => {
    throw new Error('401');
  }, browser);

  assert.equal(opened, false);
  assert.equal(closed, true);
});

test('releases the PDF from memory afterwards', async () => {
  const { browser, calls } = fakeBrowser({ location: {}, close() {} });

  await openPdf(async () => 'blob', browser);
  calls.scheduled();

  assert.equal(calls.revoked, 'blob:pdf');
});
