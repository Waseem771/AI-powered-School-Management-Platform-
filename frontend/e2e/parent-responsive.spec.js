// Every Parent Portal page, at each screen size: fits, can be tapped, and has no stray errors.
import { expect, test } from '@playwright/test';
import { API_PORT, E2E_PASSWORD } from '../playwright.config.js';
import { watchForProblems } from './helpers.js';

const API = `http://localhost:${API_PORT}`;
const PASSWORD = 'parent-responsive-pw-1';
const MIN_TOUCH_TARGET = 44;
const PAGES = [
  ['dashboard', '/parent/dashboard', 'Parent Dashboard'],
  ['attendance', '/parent/attendance', 'Attendance'],
  ['results', '/parent/results', 'Exam Results'],
  ['fees', '/parent/fees', 'Fees & Payments'],
  ['profile', '/parent/profile', 'My Profile'],
];

let username;

test.beforeAll(async ({ request }) => {
  const login = await request.post(`${API}/auth/login`, { data: { username: 'admin', password: E2E_PASSWORD } });
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const students = await (await request.get(`${API}/students`, { headers })).json();
  username = `e2e.family.${Date.now()}`;
  const created = await request.post(`${API}/parents`, {
    headers,
    data: {
      username, full_name: 'Family E2E', password: PASSWORD, relationship: 'Mother',
      student_ids: students.slice(0, 2).map((student) => student.id),
    },
  });
  expect(created.status()).toBe(201);
});

test.beforeEach(async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/parent\/dashboard/);
});

for (const [name, path, heading] of PAGES) {
  test(`parent ${name} fits and can be tapped`, async ({ page }, info) => {
    const problems = watchForProblems(page);
    await page.goto(path);
    await expect(page.getByRole('heading', { name: heading, exact: true }).first()).toBeVisible();
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: `test-results/shots/${info.project.name}-parent-${name}.png`, fullPage: true });

    const layout = await page.evaluate((minimum) => {
      const isShown = (element) => {
        const box = element.getBoundingClientRect();
        return box.width > 0 && box.height > 0 && getComputedStyle(element).visibility !== 'hidden';
      };
      const controls = [...document.querySelectorAll('main button, main a, main input, main select, main [role=combobox]')].filter(isShown);
      return {
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        tooSmall: controls.filter((element) => element.getBoundingClientRect().height < minimum).map((element) => element.outerHTML.slice(0, 80)),
        tables: [...document.querySelectorAll('table')].filter(isShown).length,
      };
    }, MIN_TOUCH_TARGET);

    expect(layout.overflow).toBeLessThanOrEqual(0);
    if (info.project.name !== 'desktop') expect(layout.tooSmall).toEqual([]);
    if (info.project.name === 'phone') expect(layout.tables).toBe(0);
    expect(problems).toEqual([]);
  });
}

test('parent pages say so when the server fails, and recover with Try again', async ({ page }) => {
  let failing = true;
  await page.route(`${API}/parent/children`, (route) => (failing ? route.fulfill({ status: 500, body: '{"detail":"boom"}' }) : route.continue()));
  await page.goto('/parent/dashboard');
  await expect(page.getByRole('alert')).toContainText('This could not be loaded');
  failing = false;
  await page.getByRole('button', { name: 'Try again' }).click();
  await expect(page.getByRole('heading', { name: 'Parent Dashboard' })).toBeVisible();
  await expect(page.getByText('Welcome, Family E2E.')).toBeVisible();
});

test('the phone menu opens, shows the parent menu only, and closes', async ({ page }, info) => {
  test.skip(info.project.name !== 'phone', 'The drawer is only used on phones.');
  await page.getByRole('button', { name: 'Open navigation menu' }).click();
  const nav = page.getByRole('navigation', { name: 'Main navigation' });
  await expect(nav.getByRole('link')).toHaveText(['Dashboard', 'Attendance', 'Results', 'Fees', 'My Profile']);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Open navigation menu' })).toBeVisible();
});
