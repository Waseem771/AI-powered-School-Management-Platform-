import { expect, test } from '@playwright/test';
import { E2E_PASSWORD } from '../playwright.config.js';
import { dialog, signIn, watchForProblems } from './helpers.js';

const TEACHER_PASSWORD = 'teacher-e2e-password-1';

async function signInAs(page, username, password) {
  await page.goto('/login');
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
}

test('an administrator creates a teacher, who sees only the teacher portal until deactivated', async ({ browser, page }) => {
  const problems = watchForProblems(page);
  const username = `e2e.teacher.${Date.now()}`;

  // Administrator creates the account.
  await signIn(page);
  await page.getByRole('link', { name: 'Teachers' }).click();
  await expect(page).toHaveURL(/\/teachers$/);
  await page.getByRole('button', { name: 'Add Teacher' }).click();
  const form = dialog(page);
  await form.getByLabel('Full name').fill('Sara E2E');
  await form.getByLabel('Username').fill(username);
  await form.getByLabel('Initial password').fill(TEACHER_PASSWORD);
  await form.getByRole('button', { name: 'Create Account' }).click();
  await expect(page.getByText('Account created for Sara E2E.')).toBeVisible();
  const row = page.locator('tr', { hasText: username });
  await expect(row.getByText('Active')).toBeVisible();

  // A duplicate is refused with a clear message.
  await page.getByRole('button', { name: 'Add Teacher' }).click();
  await dialog(page).getByLabel('Full name').fill('Someone Else');
  await dialog(page).getByLabel('Username').fill(username.toUpperCase());
  await dialog(page).getByLabel('Initial password').fill(TEACHER_PASSWORD);
  await dialog(page).getByRole('button', { name: 'Create Account' }).click();
  await expect(dialog(page).getByRole('alert')).toContainText('already taken');
  await dialog(page).getByRole('button', { name: 'Cancel' }).click();

  // The teacher, in their own browser session.
  const teacherContext = await browser.newContext();
  const teacher = await teacherContext.newPage();
  const teacherProblems = watchForProblems(teacher);
  await signInAs(teacher, username, TEACHER_PASSWORD);
  await expect(teacher).toHaveURL(/\/teacher\/dashboard$/);
  await expect(teacher.getByRole('heading', { name: 'Teacher Dashboard' })).toBeVisible();
  await expect(teacher.getByText('Welcome, Sara E2E.')).toBeVisible();
  const main = teacher.locator('#main-content');
  await expect(main.getByText('Teacher', { exact: true })).toBeVisible();
  await expect(main.getByText('Active', { exact: true })).toBeVisible();
  for (const label of ['My Classes', 'Daily Attendance', 'Student Records', 'Marks Entry']) {
    await expect(main.getByText(label, { exact: true })).toBeVisible();
  }
  await expect(main.getByText('Coming later').first()).toBeVisible();

  const nav = teacher.getByRole('navigation', { name: 'Main navigation' });
  await expect(nav.getByRole('link')).toHaveText(['Teacher Dashboard', 'My Classes', 'My Profile']);

  // Direct addresses of restricted screens go back to the portal.
  for (const path of ['/students', '/fees', '/admissions', '/teachers', '/dashboard', '/chatbot']) {
    await teacher.goto(path);
    await expect(teacher).toHaveURL(/\/teacher\/dashboard$/);
  }

  await nav.getByRole('link', { name: 'My Profile' }).click();
  await expect(teacher).toHaveURL(/\/teacher\/profile$/);
  await expect(main.getByText(username, { exact: true })).toBeVisible();
  await expect(main.getByText('Sara E2E', { exact: true })).toBeVisible();

  // Sign out works, and the old session no longer opens anything.
  await teacher.getByRole('button', { name: 'Sign Out' }).click();
  await expect(teacher).toHaveURL(/\/login$/);
  await teacher.goto('/teacher/dashboard');
  await expect(teacher).toHaveURL(/\/login$/);

  // Sign back in, then the administrator deactivates the account.
  await signInAs(teacher, username, TEACHER_PASSWORD);
  await expect(teacher).toHaveURL(/\/teacher\/dashboard$/);

  await row.getByRole('button', { name: /Deactivate/ }).click();
  await dialog(page).getByRole('button', { name: 'Deactivate' }).click();
  await expect(page.getByText('is now deactivated.')).toBeVisible();
  await expect(row.getByText('Deactivated')).toBeVisible();

  // The teacher's open session ends on the next request, with an explanation.
  await teacher.getByRole('link', { name: 'My Profile' }).click();
  await expect(teacher).toHaveURL(/\/login\?reason=ended$/);
  await expect(teacher.getByText('Your session has ended. Please sign in again.')).toBeVisible();

  // And they cannot sign in again until reactivated.
  await signInAs(teacher, username, TEACHER_PASSWORD);
  await expect(teacher.getByRole('alert')).toContainText('deactivated');
  await row.getByRole('button', { name: /Activate/ }).click();
  await expect(row.getByText('Active')).toBeVisible();
  await signInAs(teacher, username, TEACHER_PASSWORD);
  await expect(teacher).toHaveURL(/\/teacher\/dashboard$/);

  expect(problems).toEqual([]);
  expect(teacherProblems).toEqual([]);
  await teacherContext.close();
});

test('an administrator is kept out of the teacher portal and still sees the usual menu', async ({ page }) => {
  await signIn(page);
  await page.goto('/teacher/dashboard');
  await expect(page).toHaveURL(/\/dashboard$/);
  const nav = page.getByRole('navigation', { name: 'Main navigation' });
  for (const label of ['Dashboard', 'Students', 'Fees', 'Exam Results', 'Admissions', 'Teachers', 'Teacher Assignments', 'Attendance']) {
    await expect(nav.getByRole('link', { name: label })).toBeVisible();
  }
});

test('the demo password is not reused for teachers', () => {
  expect(TEACHER_PASSWORD).not.toBe(E2E_PASSWORD);
});
