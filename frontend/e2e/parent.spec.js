import { expect, test } from '@playwright/test';
import { API_PORT, E2E_PASSWORD } from '../playwright.config.js';
import { dialog, expectPdfOpens, signIn, watchForProblems } from './helpers.js';

const API = `http://localhost:${API_PORT}`;
const PARENT_PASSWORD = 'parent-e2e-password-1';
const NEW_PASSWORD = 'parent-e2e-changed-pw-2';

async function adminApi(request) {
  const login = await request.post(`${API}/auth/login`, { data: { username: 'admin', password: E2E_PASSWORD } });
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const get = async (path) => (await request.get(`${API}${path}`, { headers })).json();
  return { headers, get };
}

/** Two current students that have fee challans and exam marks. The first has also paid something. */
async function pickTwoChildren(api) {
  const invoices = await api.get('/fees');
  const withMarks = async (id) => (await api.get(`/results/${id}`)).results.length > 0;
  const paid = [...new Set(invoices.filter((i) => i.amount_paid > 0 && !i.student_archived).map((i) => i.student_id))];
  const others = [...new Set(invoices.filter((i) => !i.student_archived).map((i) => i.student_id))];
  let first = null;
  for (const id of paid) if (await withMarks(id)) { first = id; break; }
  let second = null;
  for (const id of others) if (id !== first && await withMarks(id)) { second = id; break; }
  expect(first, 'a demo student with a payment and marks').not.toBeNull();
  expect(second, 'a second demo student with marks').not.toBeNull();
  const students = await api.get('/students');
  return [first, second].map((id) => students.find((student) => student.id === id));
}

async function signInAs(page, username, password) {
  await page.goto('/login');
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
}

async function addChildInDialog(page, student) {
  const picker = dialog(page).getByRole('combobox', { name: 'Add a child' });
  await picker.fill(student.roll_number);
  await dialog(page).getByRole('option', { name: new RegExp(`#${student.roll_number},`) }).click();
}

test('an administrator creates a parent for two children, who then see only their own children\'s real records', async ({ browser, page, request }) => {
  const problems = watchForProblems(page);
  const api = await adminApi(request);
  const [first, second] = await pickTwoChildren(api);
  const username = `e2e.parent.${Date.now()}`;

  // Real records the portal must show. Attendance is entered by the school, as the portal cannot.
  const day = (offset) => new Date(Date.now() + 5 * 3600 * 1000 - offset * 86400000).toISOString().slice(0, 10);
  for (const [offset, status] of [[0, 'present'], [1, 'absent'], [2, 'late']]) {
    const saved = await request.put(`${API}/attendance/class-day`, {
      headers: api.headers,
      data: {
        date: day(offset), grade: first.grade, section: first.section,
        entries: [{ student_id: first.id, status }], reason: 'e2e setup',
      },
    });
    expect(saved.ok()).toBeTruthy();
  }
  const firstFees = await api.get(`/fees/student/${first.id}/summary`);
  const firstResults = await api.get(`/results/${first.id}`);

  // The administrator creates the account.
  await signIn(page);
  await page.getByRole('link', { name: 'Parents' }).click();
  await expect(page).toHaveURL(/\/parents$/);
  await page.getByRole('button', { name: 'Add Parent' }).click();
  const form = dialog(page);
  await form.getByLabel('Full name').fill('Imran E2E');
  await form.getByLabel('Username').fill(username);
  await form.getByLabel('Initial password').fill(PARENT_PASSWORD);
  await form.getByLabel('Relationship to the children').selectOption('Father');
  await form.getByRole('button', { name: 'Create Account' }).click();
  await expect(form.getByRole('alert')).toContainText('Add at least one child');
  await addChildInDialog(page, first);
  await addChildInDialog(page, second);
  await expect(form.getByRole('list', { name: 'Children to link' }).getByRole('listitem')).toHaveCount(2);
  await form.getByRole('button', { name: 'Create Account' }).click();
  await expect(page.getByText('Account created for Imran E2E.')).toBeVisible();
  const row = page.locator('tr', { hasText: username });
  await expect(row.getByText('Active')).toBeVisible();
  await expect(row).toContainText(first.name);
  await expect(row).toContainText(second.name);

  // A duplicate username is refused with a clear message.
  await page.getByRole('button', { name: 'Add Parent' }).click();
  await dialog(page).getByLabel('Full name').fill('Someone Else');
  await dialog(page).getByLabel('Username').fill(username.toUpperCase());
  await dialog(page).getByLabel('Initial password').fill(PARENT_PASSWORD);
  await addChildInDialog(page, second);
  await dialog(page).getByRole('button', { name: 'Create Account' }).click();
  await expect(dialog(page).getByRole('alert')).toContainText('already taken');
  await dialog(page).getByRole('button', { name: 'Cancel' }).click();

  // The parent, in their own browser session.
  const parentContext = await browser.newContext();
  const parent = await parentContext.newPage();
  const parentProblems = watchForProblems(parent);
  await signInAs(parent, username, PARENT_PASSWORD);
  await expect(parent).toHaveURL(/\/parent\/dashboard$/);
  await expect(parent.getByRole('heading', { name: 'Parent Dashboard' })).toBeVisible();
  await expect(parent.getByText('Welcome, Imran E2E.')).toBeVisible();
  const nav = parent.getByRole('navigation', { name: 'Main navigation' });
  await expect(nav.getByRole('link')).toHaveText(['Dashboard', 'Attendance', 'Results', 'Fees', 'My Profile']);

  // Dashboard: both children, with their real fee balances.
  const main = parent.locator('#main-content');
  const cardOf = (student) => main.getByRole('article', { name: student.name });
  await expect(cardOf(first)).toBeVisible();
  await expect(cardOf(second)).toBeVisible();
  if (firstFees.outstanding > 0) {
    await expect(cardOf(first)).toContainText(`Rs. ${firstFees.outstanding.toLocaleString()} to pay`);
  } else {
    await expect(cardOf(first)).toContainText('All fees paid');
  }
  await expect(cardOf(first)).toContainText('% this session');
  await expect(cardOf(second)).toContainText('No attendance recorded this month');
  // Results are not released yet.
  await expect(cardOf(first)).toContainText('No results released yet');

  // Direct addresses of every other screen go back to the portal.
  for (const path of ['/students', '/fees', '/results', '/admissions', '/parents', '/teachers', '/dashboard', '/teacher/dashboard', '/chatbot']) {
    await parent.goto(path);
    await expect(parent).toHaveURL(/\/parent\/dashboard$/);
  }

  // The server refuses too, whatever the screens say.
  const refused = await parent.evaluate(async ({ api, firstId, secondId }) => {
    const token = localStorage.getItem('educore_token');
    const status = async (path) => (await fetch(`${api}${path}`, { headers: { Authorization: `Bearer ${token}` } })).status;
    return {
      students: await status('/students'),
      fees: await status('/fees'),
      resultsOfLinkedChild: await status(`/results/${firstId}`),
      otherChild: await status('/parent/children/999999/fees'),
      linkedChild: await status(`/parent/children/${secondId}/fees`),
    };
  }, { api: API, firstId: first.id, secondId: second.id });
  expect(refused).toEqual({ students: 403, fees: 403, resultsOfLinkedChild: 403, otherChild: 404, linkedChild: 200 });

  // Attendance: real records, the percentage, and switching children.
  await cardOf(first).getByRole('link', { name: /Attendance/ }).click();
  await expect(parent).toHaveURL(/\/parent\/attendance\?child=/);
  await expect(parent.getByRole('heading', { name: 'Attendance', exact: true })).toBeVisible();
  await expect(main.getByText('66.7%').first()).toBeVisible(); // 2 of the 3 recorded days: present and late
  await expect(main.locator('table').getByText('Present', { exact: true })).toBeVisible();
  await expect(main.locator('table').getByText('Absent', { exact: true })).toBeVisible();
  await expect(main.locator('table').getByText('Late', { exact: true })).toBeVisible();
  await main.getByRole('button', { name: 'Previous month' }).click();
  await expect(main.getByRole('button', { name: 'Next month' })).toBeEnabled();
  await main.getByRole('button', { name: 'Next month' }).click();
  await expect(main.getByRole('button', { name: 'Next month' })).toBeDisabled();
  await main.getByRole('button', { name: second.name }).click();
  await expect(parent).toHaveURL(new RegExp(`child=${second.id}`));
  await expect(main.getByText('No attendance has been recorded for')).toBeVisible();
  // There is nothing on the page that changes attendance.
  await expect(main.getByRole('button', { name: /save|mark|edit|correct/i })).toHaveCount(0);

  // Results: hidden until the administrator shows them.
  await nav.getByRole('link', { name: 'Results' }).click();
  await expect(main.getByText('No results have been released yet')).toBeVisible();

  await row.getByRole('button', { name: 'Children' }).click();
  await expect(dialog(page).getByRole('list', { name: 'Linked children' }).getByRole('listitem')).toHaveCount(2);
  await dialog(page).getByRole('button', { name: 'Done' }).click();
  const finalTerm = page.locator('tr', { hasText: 'Final Term' }).first();
  await finalTerm.getByRole('button', { name: /Show to parents/ }).click();
  await dialog(page).getByRole('button', { name: 'Show to parents' }).click();
  await expect(page.getByText(/is now visible to parents\./)).toBeVisible();
  await expect(finalTerm.getByText('Visible')).toBeVisible();

  await parent.goto(`/parent/results?child=${first.id}`);
  await expect(main.getByText(`${firstResults.summary.percentage}%`).first()).toBeVisible();
  await expect(main.getByRole('row')).toHaveCount(firstResults.results.length + 1);
  for (const mark of firstResults.results) {
    await expect(main.getByRole('row', { name: new RegExp(mark.subject) }).first()).toBeVisible();
  }
  await expectPdfOpens(parent, () => main.getByRole('button', { name: 'Report card' }).click());

  // Fees: balances, challans and the receipt of a real payment.
  await nav.getByRole('link', { name: 'Fees' }).click();
  await parent.goto(`/parent/fees?child=${first.id}`);
  await expect(main.getByText('Online payment is not available.')).toBeVisible();
  await expect(main.getByRole('heading', { name: 'Payment history' })).toBeVisible();
  await expect(main.getByText(`Rs. ${firstFees.collected.toLocaleString()}`).first()).toBeVisible();
  await expectPdfOpens(parent, () => main.getByRole('button', { name: /^Challan/ }).first().click());
  await expectPdfOpens(parent, () => main.getByRole('button', { name: /^Receipt/ }).first().click());
  await expect(main.getByRole('button', { name: /pay now|record payment/i })).toHaveCount(0);

  // Profile: account details, children, password change, and log out.
  await nav.getByRole('link', { name: 'My Profile' }).click();
  await expect(main.getByText(username, { exact: true })).toBeVisible();
  await expect(main.getByText('Imran E2E', { exact: true })).toBeVisible();
  await expect(main.getByRole('list').getByText(first.name)).toBeVisible();
  await main.getByRole('button', { name: 'Change password' }).click();
  await dialog(parent).getByLabel('Current password').fill(PARENT_PASSWORD);
  await dialog(parent).getByLabel('New password', { exact: true }).fill(NEW_PASSWORD);
  await dialog(parent).getByLabel('Confirm new password').fill(NEW_PASSWORD);
  await dialog(parent).getByRole('button', { name: 'Change Password' }).click();
  await expect(parent.getByText(/Password changed/)).toBeVisible();
  await main.getByRole('button', { name: 'Log out' }).click();
  await expect(parent).toHaveURL(/\/login$/);
  await parent.goto('/parent/dashboard');
  await expect(parent).toHaveURL(/\/login$/);
  await signInAs(parent, username, PARENT_PASSWORD);
  await expect(parent.getByRole('alert')).toContainText('Incorrect username or password');
  await signInAs(parent, username, NEW_PASSWORD);
  await expect(parent).toHaveURL(/\/parent\/dashboard$/);

  // Deactivating ends the parent's open session, and they cannot sign in until reactivated.
  await row.getByRole('button', { name: /Deactivate/ }).click();
  await dialog(page).getByRole('button', { name: 'Deactivate' }).click();
  await expect(page.getByText('is now deactivated.')).toBeVisible();
  await expect(row.getByText('Deactivated')).toBeVisible();
  await parent.getByRole('link', { name: 'My Profile' }).click();
  await expect(parent).toHaveURL(/\/login\?reason=ended$/);
  await signInAs(parent, username, NEW_PASSWORD);
  await expect(parent.getByRole('alert')).toContainText('deactivated');
  await row.getByRole('button', { name: /Activate/ }).click();
  await expect(row.getByText('Active')).toBeVisible();
  await signInAs(parent, username, NEW_PASSWORD);
  await expect(parent).toHaveURL(/\/parent\/dashboard$/);

  // An administrator can unlink a child, and the parent stops seeing them at once.
  await row.getByRole('button', { name: 'Children' }).click();
  await dialog(page).getByRole('button', { name: `Remove ${second.name}` }).click();
  await expect(page.getByText(`${second.name} is no longer linked.`)).toBeVisible();
  await dialog(page).getByRole('button', { name: 'Done' }).click();
  await parent.reload();
  await expect(cardOf(second)).toHaveCount(0);
  await expect(cardOf(first)).toBeVisible();

  expect(problems).toEqual([]);
  expect(parentProblems).toEqual([]);
  await parentContext.close();
});

test('an administrator is kept out of the parent portal and still sees the usual menu', async ({ page }) => {
  await signIn(page);
  await page.goto('/parent/dashboard');
  await expect(page).toHaveURL(/\/dashboard$/);
  const nav = page.getByRole('navigation', { name: 'Main navigation' });
  for (const label of ['Dashboard', 'Students', 'Fees', 'Exam Results', 'Admissions', 'Teachers', 'Teacher Assignments', 'Attendance', 'Parents']) {
    await expect(nav.getByRole('link', { name: label, exact: true })).toBeVisible();
  }
});

test('the demo password is not reused for parents', () => {
  expect(PARENT_PASSWORD).not.toBe(E2E_PASSWORD);
  expect(NEW_PASSWORD).not.toBe(PARENT_PASSWORD);
});
