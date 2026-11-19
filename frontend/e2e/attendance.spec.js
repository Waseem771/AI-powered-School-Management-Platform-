import { expect, test } from '@playwright/test';
import { dialog, signIn, watchForProblems } from './helpers.js';

const TEACHER_PASSWORD = 'teacher-e2e-password-1';

async function signInAs(page, username, password) {
  await page.goto('/login');
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
}

test('assign a class, take attendance, correct it, and see it in the administrator reports', async ({ browser, page }) => {
  const problems = watchForProblems(page);
  const username = `e2e.att.${Date.now()}`;

  // Administrator creates a teacher and assigns Grade 8, Section A.
  await signIn(page);
  await page.getByRole('link', { name: 'Teachers', exact: true }).click();
  await page.getByRole('button', { name: 'Add Teacher' }).click();
  await dialog(page).getByLabel('Full name').fill('Attendance Tester');
  await dialog(page).getByLabel('Username').fill(username);
  await dialog(page).getByLabel('Initial password').fill(TEACHER_PASSWORD);
  await dialog(page).getByRole('button', { name: 'Create Account' }).click();
  await expect(page.getByText('Account created for Attendance Tester.')).toBeVisible();

  await page.getByRole('link', { name: 'Teacher Assignments' }).click();
  await page.getByRole('button', { name: 'Assign Teacher' }).click();
  await dialog(page).getByLabel('Teacher').selectOption({ label: `Attendance Tester (${username})` });
  await dialog(page).getByLabel('Grade').selectOption('Grade 8');
  await dialog(page).getByLabel('Section').selectOption('A');
  await dialog(page).getByRole('button', { name: 'Save' }).click();
  await expect(page.getByText('Teacher assigned.')).toBeVisible();
  const row = page.locator('tr', { hasText: username });
  await expect(row).toContainText('Grade 8-A');

  // A duplicate is refused.
  await page.getByRole('button', { name: 'Assign Teacher' }).click();
  await dialog(page).getByLabel('Teacher').selectOption({ label: `Attendance Tester (${username})` });
  await dialog(page).getByLabel('Grade').selectOption('Grade 8');
  await dialog(page).getByLabel('Section').selectOption('A');
  await dialog(page).getByRole('button', { name: 'Save' }).click();
  await expect(dialog(page).getByRole('alert')).toContainText('already assigned');
  await dialog(page).getByRole('button', { name: 'Cancel' }).click();

  // The teacher sees only that class and takes attendance.
  const teacherContext = await browser.newContext();
  const teacher = await teacherContext.newPage();
  const teacherProblems = watchForProblems(teacher);
  await signInAs(teacher, username, TEACHER_PASSWORD);
  await expect(teacher).toHaveURL(/\/teacher\/dashboard$/);
  await teacher.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'My Classes' }).click();
  const main = teacher.locator('#main-content');
  await expect(main.getByRole('link')).toHaveCount(1);
  await expect(main).toContainText('Grade 8');
  await expect(main).toContainText('Not submitted');
  await main.getByRole('link').click();
  await expect(teacher.getByRole('heading', { name: 'Grade 8-A' })).toBeVisible();
  await expect(main.getByText('Student roster')).toBeVisible();
  await teacher.getByRole('link', { name: 'Daily Attendance' }).first().click();

  // Saving with students left unmarked is refused, and nothing is counted as absent.
  await expect(teacher.getByRole('heading', { name: 'Daily Attendance' })).toBeVisible();
  const groups = teacher.getByRole('radiogroup');
  await expect(groups.first()).toBeVisible();
  const total = await groups.count();
  expect(total).toBeGreaterThan(2);
  await groups.nth(0).getByRole('radio', { name: 'Present' }).click();
  await teacher.getByRole('button', { name: 'Save Attendance' }).click();
  await expect(teacher.getByRole('alert')).toContainText('not marked yet');

  await groups.nth(0).getByRole('radio', { name: 'Absent' }).click();
  await teacher.getByRole('button', { name: /Mark unmarked as Present/ }).click();
  await expect(groups.nth(1).getByRole('radio', { name: 'Present' })).toHaveAttribute('aria-checked', 'true');
  await expect(groups.nth(0).getByRole('radio', { name: 'Absent' })).toHaveAttribute('aria-checked', 'true');
  await groups.nth(2).getByRole('radio', { name: 'Late' }).click();
  await teacher.getByRole('button', { name: 'Save Attendance' }).click();
  await expect(teacher.getByText(/Attendance saved for \d+ students?\./)).toBeVisible();
  await expect(teacher.getByText('Submitted', { exact: true })).toBeVisible();

  // Correcting a saved record needs a reason.
  await groups.nth(0).getByRole('radio', { name: 'Present' }).click();
  await teacher.getByRole('button', { name: 'Save Attendance' }).click();
  await expect(teacher.getByRole('alert')).toContainText('why you are correcting');
  await teacher.getByLabel(/Reason for correcting/).fill('Arrived after the bell');
  await teacher.getByRole('button', { name: 'Save Attendance' }).click();
  await expect(teacher.getByText(/1 correction recorded/)).toBeVisible();
  await expect(teacher.getByText('Corrections made')).toBeVisible();
  await expect(teacher.getByText('Reason: Arrived after the bell')).toBeVisible();

  // History lists the day.
  await page.waitForTimeout(0);
  await teacher.goto(teacher.url().replace(/\/attendance.*$/, '/history'));
  await expect(teacher.locator('#main-content')).toContainText('corrected');

  // Another class is not reachable.
  await teacher.goto('/teacher/classes/99999');
  await expect(teacher.getByText(/not assigned to this class/i)).toBeVisible();
  // And the administrator pages are not.
  await teacher.goto('/attendance');
  await expect(teacher).toHaveURL(/\/teacher\/dashboard$/);

  // Administrator sees it: this class submitted, the others not submitted rather than absent.
  await page.getByRole('link', { name: 'Attendance', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Attendance', exact: true })).toBeVisible();
  const classRow = page.locator('tr', { hasText: 'Grade 8-A' });
  await expect(classRow).toContainText('Submitted');
  await expect(classRow).toContainText('Attendance Tester');
  await expect(page.locator('tr', { hasText: 'Grade 6-A' })).toContainText('Not submitted');
  await expect(page.getByText('Classes not submitted')).toBeVisible();

  // Export downloads a CSV, and the report page opens.
  const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Export CSV' }).click()]);
  expect(download.suggestedFilename()).toMatch(/^attendance-\d{4}-\d{2}-\d{2}-to-\d{4}-\d{2}-\d{2}\.csv$/);
  await page.getByRole('link', { name: 'Printable report' }).click();
  await expect(page.getByRole('heading', { name: 'Attendance Report' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Print report' })).toBeVisible();
  await page.goBack();

  // Administrator corrections and the corrections log.
  await page.locator('tr', { hasText: 'Grade 8-A' }).getByRole('button', { name: /View \/ correct/ }).click();
  await expect(dialog(page)).toContainText('Corrections made');
  await dialog(page).getByRole('button', { name: 'Close', exact: true }).last().click();
  await page.getByRole('button', { name: 'Corrections log' }).click();
  await expect(page.getByRole('cell', { name: 'Arrived after the bell' })).toBeVisible();

  // Removing the assignment takes the class away from the teacher but keeps the attendance.
  await page.getByRole('link', { name: 'Teacher Assignments' }).click();
  await page.locator('tr', { hasText: username }).getByRole('button', { name: /Remove/ }).click();
  await dialog(page).getByRole('button', { name: 'Remove' }).click();
  await expect(page.getByText('Assignment removed.')).toBeVisible();
  await teacher.goto('/teacher/classes');
  await expect(teacher.getByText('No classes assigned yet')).toBeVisible();

  expect(problems).toEqual([]);
  expect(teacherProblems).toEqual([]);
  await teacherContext.close();
});
