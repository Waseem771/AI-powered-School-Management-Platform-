import { expect } from '@playwright/test';
import { API_PORT, E2E_PASSWORD } from '../playwright.config.js';

export const API_GLOB = `http://localhost:${API_PORT}/**`;

export async function signIn(page) {
  await page.goto('/login');
  await page.getByLabel('Username').fill('admin');
  await page.getByLabel('Password').fill(E2E_PASSWORD);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}

/** Records anything that should never happen: script errors and security policy refusals. */
export function watchForProblems(page) {
  const problems = [];
  page.on('pageerror', (error) => problems.push(`page error: ${error.message}`));
  page.on('console', (message) => {
    const text = message.text();
    if (/content security policy|refused to/i.test(text)) problems.push(`console: ${text}`);
  });
  return problems;
}

/** Clicks something that opens a PDF, and checks a PDF tab really opened. */
export async function expectPdfOpens(page, click) {
  const [tab] = await Promise.all([page.context().waitForEvent('page'), click()]);
  const refused = [];
  tab.on('console', (message) => {
    if (/content security policy|refused to/i.test(message.text())) refused.push(message.text());
  });
  await expect.poll(() => tab.url(), { timeout: 20_000 }).toMatch(/^blob:/);
  await tab.waitForLoadState();
  // The browser's PDF viewer really loaded it, under the same security policy as the app.
  expect(await tab.evaluate(() => document.contentType)).toBe('application/pdf');
  expect(refused).toEqual([]);
  await tab.close();
}

export function dialog(page) {
  return page.locator('[role=dialog][aria-modal=true]');
}
