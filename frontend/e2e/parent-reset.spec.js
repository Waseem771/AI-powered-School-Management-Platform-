import { expect, test } from '@playwright/test';
import { API_PORT, E2E_PASSWORD } from '../playwright.config.js';
import { dialog, signIn, watchForProblems } from './helpers.js';

const API = `http://localhost:${API_PORT}`;
const ORIGINAL = 'parent-reset-original-1';
const TEMPORARY = 'temporary-reset-e2e-1';
const CHOSEN = 'parent-reset-chosen-2';

async function signInAs(page, username, password) {
  await page.goto('/login');
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
}

test('an administrator resets a parent password: sessions end, the parent must choose a new one', async ({ browser, page, request }) => {
  const problems = watchForProblems(page);
  const login = await request.post(`${API}/auth/login`, { data: { username: 'admin', password: E2E_PASSWORD } });
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const students = await (await request.get(`${API}/students`, { headers })).json();
  const username = `e2e.reset.${Date.now()}`;
  const created = await request.post(`${API}/parents`, {
    headers, data: { username, full_name: 'Reset E2E', password: ORIGINAL, student_ids: [students[0].id] },
  });
  expect(created.status()).toBe(201);

  // The parent is signed in on another device.
  const parentContext = await browser.newContext();
  const parent = await parentContext.newPage();
  const parentProblems = watchForProblems(parent);
  await signInAs(parent, username, ORIGINAL);
  await expect(parent).toHaveURL(/\/parent\/dashboard$/);
  const oldToken = await parent.evaluate(() => localStorage.getItem('educore_token'));

  // The administrator opens the dialog. Mistakes and weak passwords are explained and change nothing.
  await signIn(page);
  await page.getByRole('link', { name: 'Parents' }).click();
  const row = page.locator('tr', { hasText: username });
  await expect(row.getByText('Active')).toBeVisible();
  await expect(row.getByText('Must change password')).toHaveCount(0);
  await row.getByRole('button', { name: /Reset password/ }).click();
  const form = dialog(page);
  await expect(form.getByRole('heading', { name: 'Reset password for Reset E2E?' })).toBeVisible();
  await form.getByRole('button', { name: 'Reset Password' }).click();
  await expect(form.getByRole('alert')).toContainText('at least 10 characters');
  await form.getByLabel('New temporary password').fill(TEMPORARY);
  await form.getByLabel('Confirm the password').fill('something-else-entirely');
  await form.getByRole('button', { name: 'Reset Password' }).click();
  await expect(form.getByRole('alert')).toContainText('do not match');
  await form.getByLabel('New temporary password').fill('password123');
  await form.getByLabel('Confirm the password').fill('password123');
  await form.getByRole('button', { name: 'Reset Password' }).click();
  await expect(form.getByRole('alert')).toContainText('too common');
  // Nothing happened yet: the old password still signs in.
  expect((await request.post(`${API}/auth/login`, { data: { username, password: ORIGINAL } })).status()).toBe(200);

  // A good password is accepted. The password is never shown on the page.
  await form.getByLabel('New temporary password').fill(TEMPORARY);
  await form.getByLabel('Confirm the password').fill(TEMPORARY);
  await form.getByRole('button', { name: 'Reset Password' }).click();
  await expect(page.getByText('Password reset for Reset E2E.')).toBeVisible();
  await expect(row.getByText('Must change password')).toBeVisible();
  expect(await page.content()).not.toContain(TEMPORARY);

  // The old session is over, with an explanation, and the old password no longer works.
  expect((await request.get(`${API}/parent/children`, { headers: { Authorization: `Bearer ${oldToken}` } })).status()).toBe(401);
  await parent.getByRole('link', { name: 'My Profile' }).click();
  await expect(parent).toHaveURL(/\/login\?reason=ended$/);
  await signInAs(parent, username, ORIGINAL);
  await expect(parent.getByRole('alert')).toContainText('Incorrect username or password');

  // The temporary password works, but only for choosing a new one.
  await signInAs(parent, username, TEMPORARY);
  await expect(parent).toHaveURL(/\/change-password$/);
  await expect(parent.getByRole('heading', { name: 'Choose a new password' })).toBeVisible();
  for (const path of ['/parent/dashboard', '/parent/fees', '/students', '/dashboard']) {
    await parent.goto(path);
    await expect(parent).toHaveURL(/\/change-password$/);
  }
  // Clearing the browser's own flag does not help: the server still refuses.
  const refused = await parent.evaluate(async (api) => {
    const token = localStorage.getItem('educore_token');
    const response = await fetch(`${api}/parent/children`, { headers: { Authorization: `Bearer ${token}` } });
    return { status: response.status, body: await response.json() };
  }, API);
  expect(refused.status).toBe(403);
  await parent.evaluate(() => localStorage.setItem('educore_user', JSON.stringify({ username: 'x', role: 'parent' })));
  await parent.goto('/parent/dashboard');
  await expect(parent).toHaveURL(/\/change-password$/);

  // Mistakes on this page are explained.
  await parent.getByLabel('Temporary password').fill(TEMPORARY);
  await parent.getByLabel('New password', { exact: true }).fill('short');
  await parent.getByLabel('Confirm new password').fill('short');
  await parent.getByRole('button', { name: 'Change Password' }).click();
  await expect(parent.getByRole('alert')).toContainText('at least 10 characters');
  await parent.getByLabel('New password', { exact: true }).fill(TEMPORARY);
  await parent.getByLabel('Confirm new password').fill(TEMPORARY);
  await parent.getByRole('button', { name: 'Change Password' }).click();
  await expect(parent.getByRole('alert')).toContainText('different');

  // Choosing a real new password opens the portal.
  await parent.getByLabel('New password', { exact: true }).fill(CHOSEN);
  await parent.getByLabel('Confirm new password').fill(CHOSEN);
  await parent.getByRole('button', { name: 'Change Password' }).click();
  await expect(parent).toHaveURL(/\/parent\/dashboard$/);
  await expect(parent.getByRole('heading', { name: 'Parent Dashboard' })).toBeVisible();
  await parent.goto('/change-password');
  await expect(parent).toHaveURL(/\/parent\/dashboard$/);

  // The administrator's list clears the flag, and the temporary password is dead.
  await page.reload();
  await expect(row.getByText('Active')).toBeVisible();
  await expect(row.getByText('Must change password')).toHaveCount(0);
  expect((await request.post(`${API}/auth/login`, { data: { username, password: TEMPORARY } })).status()).toBe(401);
  expect((await request.post(`${API}/auth/login`, { data: { username, password: CHOSEN } })).status()).toBe(200);

  // The administrator's own sign-in was never touched.
  expect((await request.post(`${API}/auth/login`, { data: { username: 'admin', password: E2E_PASSWORD } })).status()).toBe(200);

  expect(problems).toEqual([]);
  expect(parentProblems).toEqual([]);
  await parentContext.close();
});

test('the sign-out option on the forced change page works', async ({ browser, request }) => {
  const login = await request.post(`${API}/auth/login`, { data: { username: 'admin', password: E2E_PASSWORD } });
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const students = await (await request.get(`${API}/students`, { headers })).json();
  const username = `e2e.reset.out.${Date.now()}`;
  const created = await request.post(`${API}/parents`, {
    headers, data: { username, full_name: 'Reset Out', password: ORIGINAL, student_ids: [students[1].id] },
  });
  const parentId = (await created.json()).id;
  const reset = await request.post(`${API}/parents/${parentId}/reset-password`, { headers, data: { new_password: TEMPORARY } });
  expect(reset.status()).toBe(200);

  const context = await browser.newContext();
  const page = await context.newPage();
  await signInAs(page, username, TEMPORARY);
  await expect(page).toHaveURL(/\/change-password$/);
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goto('/change-password');
  await expect(page).toHaveURL(/\/login$/);
  await context.close();
});

test('the reset option is only on the administrator Parents page', async ({ page }) => {
  await signIn(page);
  await page.goto('/parents');
  await expect(page.getByRole('heading', { name: 'Parents', exact: true })).toBeVisible();
  await page.goto('/change-password');
  await expect(page).toHaveURL(/\/dashboard$/); // an administrator with nothing to change is sent home
});
