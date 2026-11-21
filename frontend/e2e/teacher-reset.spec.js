import { expect, test } from '@playwright/test';
import { API_PORT, E2E_PASSWORD } from '../playwright.config.js';
import { dialog, signIn, watchForProblems } from './helpers.js';

const API = `http://localhost:${API_PORT}`;
const ORIGINAL = 'teacher-reset-original-1';
const TEMPORARY = 'temporary-teacher-e2e-1';
const CHOSEN = 'teacher-reset-chosen-2';

async function signInAs(page, username, password) {
  await page.goto('/login');
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
}

test('an administrator resets a forgotten teacher password: sessions end, the teacher must choose a new one', async ({ browser, page, request }) => {
  const problems = watchForProblems(page);
  const login = await request.post(`${API}/auth/login`, { data: { username: 'admin', password: E2E_PASSWORD } });
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const username = `e2e.forgot.${Date.now()}`;
  const created = await request.post(`${API}/teachers`, {
    headers, data: { username, full_name: 'Forgot E2E', password: ORIGINAL },
  });
  expect(created.status()).toBe(201);

  // The teacher is signed in on another device.
  const teacherContext = await browser.newContext();
  const teacher = await teacherContext.newPage();
  const teacherProblems = watchForProblems(teacher);
  await signInAs(teacher, username, ORIGINAL);
  await expect(teacher).toHaveURL(/\/teacher\/dashboard$/);
  const oldToken = await teacher.evaluate(() => localStorage.getItem('educore_token'));

  // The administrator opens the dialog. Mistakes and weak passwords are explained and change nothing.
  await signIn(page);
  await page.getByRole('link', { name: 'Teachers', exact: true }).click();
  const row = page.locator('tr', { hasText: username });
  await expect(row.getByText('Active')).toBeVisible();
  await expect(row.getByText('Must change password')).toHaveCount(0);
  await row.getByRole('button', { name: /Reset password/ }).click();
  const form = dialog(page);
  await expect(form.getByRole('heading', { name: 'Reset password for Forgot E2E?' })).toBeVisible();
  await expect(form).toContainText('Their classes and records are not changed.');
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
  expect((await request.post(`${API}/auth/login`, { data: { username, password: ORIGINAL } })).status()).toBe(200);

  // A good password is accepted, and is never shown on the page.
  await form.getByLabel('New temporary password').fill(TEMPORARY);
  await form.getByLabel('Confirm the password').fill(TEMPORARY);
  await form.getByRole('button', { name: 'Reset Password' }).click();
  await expect(page.getByText('Password reset for Forgot E2E.')).toBeVisible();
  await expect(row.getByText('Must change password')).toBeVisible();
  expect(await page.content()).not.toContain(TEMPORARY);

  // The old session is over, and the old password no longer works.
  expect((await request.get(`${API}/teacher/classes`, { headers: { Authorization: `Bearer ${oldToken}` } })).status()).toBe(401);
  await teacher.getByRole('link', { name: 'My Profile' }).click();
  await expect(teacher).toHaveURL(/\/login\?reason=ended$/);
  await signInAs(teacher, username, ORIGINAL);
  await expect(teacher.getByRole('alert')).toContainText('Incorrect username or password');

  // The temporary password works, but only for choosing a new one.
  await signInAs(teacher, username, TEMPORARY);
  await expect(teacher).toHaveURL(/\/change-password$/);
  for (const path of ['/teacher/dashboard', '/teacher/classes', '/students']) {
    await teacher.goto(path);
    await expect(teacher).toHaveURL(/\/change-password$/);
  }
  const refused = await teacher.evaluate(async (api) => {
    const token = localStorage.getItem('educore_token');
    return (await fetch(`${api}/teacher/classes`, { headers: { Authorization: `Bearer ${token}` } })).status;
  }, API);
  expect(refused).toBe(403);

  await teacher.getByLabel('Temporary password').fill(TEMPORARY);
  await teacher.getByLabel('New password', { exact: true }).fill(CHOSEN);
  await teacher.getByLabel('Confirm new password').fill(CHOSEN);
  await teacher.getByRole('button', { name: 'Change Password' }).click();
  await expect(teacher).toHaveURL(/\/teacher\/dashboard$/);
  await expect(teacher.getByRole('heading', { name: 'Teacher Dashboard' })).toBeVisible();
  await expect(teacher.getByText('Welcome, Forgot E2E.')).toBeVisible();

  // The administrator's list clears the flag, and the temporary password is dead.
  await page.reload();
  await expect(row.getByText('Active')).toBeVisible();
  await expect(row.getByText('Must change password')).toHaveCount(0);
  expect((await request.post(`${API}/auth/login`, { data: { username, password: TEMPORARY } })).status()).toBe(401);
  expect((await request.post(`${API}/auth/login`, { data: { username, password: CHOSEN } })).status()).toBe(200);
  expect((await request.post(`${API}/auth/login`, { data: { username: 'admin', password: E2E_PASSWORD } })).status()).toBe(200);

  expect(problems).toEqual([]);
  expect(teacherProblems).toEqual([]);
  await teacherContext.close();
});
