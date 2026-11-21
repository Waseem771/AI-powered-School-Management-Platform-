import fs from 'node:fs';
import path from 'node:path';
import { expect, test } from '@playwright/test';
import { API_PORT, E2E_PASSWORD, OUTBOX_DIR } from '../playwright.config.js';
import { dialog, signIn, watchForProblems } from './helpers.js';

const API = `http://localhost:${API_PORT}`;
const ORIGINAL = 'self-service-original-1';
const CHOSEN = 'self-service-chosen-2';
const GENERIC = /a reset link is on its way/;

// Mail is stored quoted-printable (long lines are folded and "=" is written "=3D"), as a mail program would read it.
function decode(text) {
  return text.replace(/=\r?\n/g, '').replace(/=([0-9A-F]{2})/g, (_, hex) => String.fromCharCode(parseInt(hex, 16)));
}

/** Every email written to the local outbox for this address (nothing is ever really sent). */
function mailsTo(address) {
  if (!fs.existsSync(OUTBOX_DIR)) return [];
  return fs.readdirSync(OUTBOX_DIR)
    .filter((name) => name.endsWith('.eml'))
    .map((name) => decode(fs.readFileSync(path.join(OUTBOX_DIR, name), 'utf8')))
    .filter((text) => new RegExp(`^To: ${address.replace('.', '\\.')}\\s*$`, 'mi').test(text));
}

function linkIn(mail) {
  const found = mail.match(/https?:\/\/\S+\/reset-password#token=[A-Za-z0-9_-]+/);
  expect(found, 'the email holds a reset link').not.toBeNull();
  return found[0];
}

async function adminHeaders(request) {
  const login = await request.post(`${API}/auth/login`, { data: { username: 'admin', password: E2E_PASSWORD } });
  return { Authorization: `Bearer ${(await login.json()).access_token}` };
}

async function askForLink(page, email) {
  await page.goto('/forgot-password');
  await page.getByLabel('Email address').fill(email);
  await page.getByRole('button', { name: 'Send reset link' }).click();
  await expect(page.getByRole('status')).toContainText(GENERIC);
}

test('a teacher resets a forgotten password by email, and an administrator manages the address', async ({ browser, page, request }) => {
  const problems = watchForProblems(page);
  const headers = await adminHeaders(request);
  const stamp = Date.now();
  const username = `e2e.self.${stamp}`;
  const email = `e2e.self.${stamp}@example.test`;
  const unknown = `nobody.${stamp}@example.test`;
  const created = await request.post(`${API}/teachers`, { headers, data: { username, full_name: 'Self Service E2E', email, password: ORIGINAL } });
  expect(created.status()).toBe(201);

  // Signed in on another device before the reset.
  const otherContext = await browser.newContext();
  const other = await otherContext.newPage();
  await other.goto('/login');
  await other.getByLabel('Username').fill(username);
  await other.getByLabel('Password').fill(ORIGINAL);
  await other.getByRole('button', { name: 'Sign In' }).click();
  await expect(other).toHaveURL(/\/teacher\/dashboard$/);
  const oldToken = await other.evaluate(() => localStorage.getItem('educore_token'));

  // From the sign-in page. A bad address is explained, and an unknown one gets exactly the same answer.
  await page.goto('/login');
  await page.getByRole('link', { name: 'Forgot password?' }).click();
  await expect(page).toHaveURL(/\/forgot-password$/);
  await page.getByLabel('Email address').fill('not-an-email');
  await page.getByRole('button', { name: 'Send reset link' }).click();
  await expect(page.getByRole('alert')).toContainText('Enter the email address');
  await page.getByLabel('Email address').fill(`${unknown},other@example.test`);
  await page.getByRole('button', { name: 'Send reset link' }).click();
  await expect(page.getByRole('alert')).toContainText('Enter the email address');
  await askForLink(page, unknown);
  const unknownAnswer = await page.getByRole('status').innerText();
  await askForLink(page, email);
  expect(await page.getByRole('status').innerText()).toBe(unknownAnswer);

  // The email arrives only for the real address, and the page never shows the link.
  await expect.poll(() => mailsTo(email).length).toBe(1);
  expect(mailsTo(unknown)).toHaveLength(0);
  expect(await page.content()).not.toContain('reset-password#token');
  const link = linkIn(mailsTo(email)[0]);
  expect(mailsTo(email)[0]).toContain('60 minutes');

  // The link opens the reset page and the token is removed from the address bar.
  await page.goto(link);
  await expect(page.getByRole('heading', { name: 'Choose a new password' })).toBeVisible();
  await expect(page.getByLabel('New password', { exact: true })).toBeVisible();
  expect(page.url()).not.toContain('token');
  await page.getByLabel('New password', { exact: true }).fill('short');
  await page.getByLabel('Confirm new password').fill('short');
  await page.getByRole('button', { name: 'Change Password' }).click();
  await expect(page.getByRole('alert')).toContainText('at least 10 characters');
  await page.getByLabel('New password', { exact: true }).fill(CHOSEN);
  await page.getByLabel('Confirm new password').fill('something-else-entirely');
  await page.getByRole('button', { name: 'Change Password' }).click();
  await expect(page.getByRole('alert')).toContainText('do not match');
  await page.getByLabel('New password', { exact: true }).fill('password123');
  await page.getByLabel('Confirm new password').fill('password123');
  await page.getByRole('button', { name: 'Change Password' }).click();
  await expect(page.getByRole('alert')).toContainText('too common'); // refused, and the link is not used up
  await page.getByLabel('New password', { exact: true }).fill(CHOSEN);
  await page.getByLabel('Confirm new password').fill(CHOSEN);
  await page.getByRole('button', { name: 'Change Password' }).click();
  await expect(page.getByRole('status')).toContainText('Your password has been changed');
  expect(await page.content()).not.toContain(CHOSEN);

  // The old session and password are dead, the new one works, and the link cannot be used again.
  expect((await request.get(`${API}/teacher/classes`, { headers: { Authorization: `Bearer ${oldToken}` } })).status()).toBe(401);
  expect((await request.post(`${API}/auth/login`, { data: { username, password: ORIGINAL } })).status()).toBe(401);
  await page.getByRole('link', { name: 'Go to sign in' }).click();
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(CHOSEN);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/teacher\/dashboard$/);
  await expect.poll(() => mailsTo(email).length).toBe(2); // the "your password was changed" notice
  await page.goto(link);
  await expect(page.getByRole('alert')).toContainText('not valid any more');
  await expect(page.getByRole('link', { name: 'Ask for a new link' })).toBeVisible();

  // The administrator changes the address, after confirming their own password.
  const adminContext = await browser.newContext();
  const admin = await adminContext.newPage();
  const adminProblems = watchForProblems(admin);
  await signIn(admin);
  await admin.getByRole('link', { name: 'Teachers', exact: true }).click();
  const row = admin.locator('tr', { hasText: username });
  await expect(row).toContainText(email);
  await row.getByRole('button', { name: /Change email/ }).click();
  const form = dialog(admin);
  const newEmail = `e2e.moved.${stamp}@example.test`;
  await form.getByLabel('Email address').fill(`${newEmail},second@example.test`);
  await form.getByLabel('Your administrator password').fill(E2E_PASSWORD);
  await form.getByRole('button', { name: 'Save Email' }).click();
  await expect(form.getByRole('alert')).toContainText('one valid email address');
  await form.getByLabel('Your administrator password').fill('');
  await form.getByLabel('Email address').fill(newEmail);
  await form.getByRole('button', { name: 'Save Email' }).click();
  await expect(form.getByRole('alert')).toContainText('administrator password');
  await form.getByLabel('Your administrator password').fill('definitely-not-it');
  await form.getByRole('button', { name: 'Save Email' }).click();
  await expect(form.getByRole('alert')).toContainText('incorrect');
  await form.getByLabel('Your administrator password').fill(E2E_PASSWORD);
  await form.getByRole('button', { name: 'Save Email' }).click();
  await expect(admin.getByText('Email address saved for Self Service E2E.')).toBeVisible();
  await expect(row).toContainText(newEmail);
  expect(await admin.content()).not.toContain(E2E_PASSWORD);

  // The old address is told, and no longer receives links. The new one does.
  await expect.poll(() => mailsTo(email).some((mail) => /address on your .* account was changed/i.test(mail))).toBe(true);
  const before = mailsTo(email).length;
  await askForLink(page, email);
  await askForLink(page, newEmail);
  await expect.poll(() => mailsTo(newEmail).length).toBe(1);
  expect(mailsTo(email)).toHaveLength(before);

  expect(problems).toEqual([]);
  expect(adminProblems).toEqual([]);
  await otherContext.close();
  await adminContext.close();
});

test('a parent resets a forgotten password by email and reaches the Parent Portal; bad links are refused', async ({ page, request }) => {
  const problems = watchForProblems(page);
  const headers = await adminHeaders(request);
  const students = await (await request.get(`${API}/students`, { headers })).json();
  const stamp = Date.now();
  const username = `e2e.parent.self.${stamp}`;
  const email = `e2e.parent.self.${stamp}@example.test`;
  const created = await request.post(`${API}/parents`, {
    headers, data: { username, full_name: 'Parent Self E2E', email, password: ORIGINAL, student_ids: [students[0].id] },
  });
  expect(created.status()).toBe(201);

  // A made-up or missing link is refused with one plain message.
  await page.goto('/reset-password#token=not-a-real-link');
  await expect(page.getByRole('alert')).toContainText('not valid any more');
  await page.goto('/reset-password');
  await expect(page.getByRole('alert')).toContainText('not valid any more');

  await askForLink(page, email);
  await expect.poll(() => mailsTo(email).length).toBe(1);
  await page.goto(linkIn(mailsTo(email)[0]));
  await page.getByLabel('New password', { exact: true }).fill(CHOSEN);
  await page.getByLabel('Confirm new password').fill(CHOSEN);
  await page.getByRole('button', { name: 'Change Password' }).click();
  await expect(page.getByRole('status')).toContainText('Your password has been changed');

  await page.getByRole('link', { name: 'Go to sign in' }).click();
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(CHOSEN);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/parent\/dashboard$/);
  expect(problems).toEqual([]);
});
