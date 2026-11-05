// Every page, at each screen size: fits, can be tapped, reports failures, and has working links.
import { expect, test } from '@playwright/test';
import { API_GLOB, signIn, watchForProblems } from './helpers.js';

const PAGES = [
  ['dashboard', '/dashboard', 'Dashboard'],
  ['students', '/students', 'Students'],
  ['fees', '/fees', 'Fees'],
  ['results', '/results', 'Exam Results'],
  ['early-warning', '/at-risk', 'Academic Early Warning'],
  ['assistant', '/chatbot', null],
  ['admissions', '/admissions', 'Admissions'],
];
const FAILABLE_PAGES = PAGES.filter(([name]) => ['dashboard', 'students', 'fees', 'early-warning'].includes(name));
const MIN_TOUCH_TARGET = 44;

test.beforeEach(async ({ page }) => {
  await signIn(page);
});

for (const [name, path, heading] of PAGES) {
  test(`${name} fits and can be tapped`, async ({ page }, info) => {
    const problems = watchForProblems(page);
    await page.goto(path);
    if (heading) await expect(page.getByRole('heading', { name: heading, exact: true }).first()).toBeVisible();
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: info.outputPath(`${name}.png`), fullPage: true });
    await page.screenshot({ path: `test-results/shots/${info.project.name}-${name}.png`, fullPage: true });

    const layout = await page.evaluate((minimum) => {
      const isShown = (element) => {
        const box = element.getBoundingClientRect();
        return box.width > 0 && box.height > 0 && getComputedStyle(element).visibility !== 'hidden';
      };
      const controls = [...document.querySelectorAll('main button, main a, main input:not([type=range]):not([type=checkbox]), main select, main [role=combobox]')].filter(isShown);
      return {
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        tooSmall: controls.filter((element) => element.getBoundingClientRect().height < minimum).map((element) => element.outerHTML.slice(0, 80)),
        tables: [...document.querySelectorAll('table')].filter(isShown).length,
      };
    }, MIN_TOUCH_TARGET);

    expect(layout.overflow).toBeLessThanOrEqual(0);
    if (info.project.name !== 'desktop') expect(layout.tooSmall).toEqual([]);
    if (info.project.name === 'phone' && ['students', 'fees'].includes(name)) expect(layout.tables).toBe(0);
    expect(problems).toEqual([]);
  });
}

for (const [name, path] of FAILABLE_PAGES) {
  test(`${name} reports a failure, and Try again works`, async ({ page }) => {
    await page.route(API_GLOB, (route) => route.abort());
    await page.goto(path);
    const alert = page.locator('main [role=alert]').first();
    await expect(alert).toContainText('Could not reach the server');
    await expect(page.locator('main')).not.toContainText('Rs. 0');

    await page.unroute(API_GLOB);
    await page.getByRole('button', { name: 'Try again' }).first().click();
    await expect(page.locator('main [role=alert]')).toHaveCount(0);
  });
}

test('results report a failure, and Try again works', async ({ page }) => {
  await page.goto('/results');
  await page.getByRole('combobox').fill('Danish');
  const option = page.getByRole('option', { name: /Danish Memon/ });
  await expect(option).toBeVisible();
  await page.route(API_GLOB, (route) => route.abort());
  await option.click();
  await expect(page.locator('main [role=alert]').first()).toContainText('Could not reach the server');
  await expect(page.locator('main')).not.toContainText('Promoted');

  await page.unroute(API_GLOB);
  await page.getByRole('button', { name: 'Try again' }).click();
  await expect(page.locator('main').getByText('Pakistan Studies').locator('visible=true').first()).toBeVisible();
});

test('long lists grow on request', async ({ page }) => {
  await page.goto('/fees');
  const rows = page.locator('main li:visible, main tbody tr:visible');
  await expect(rows).toHaveCount(25);
  await page.getByRole('button', { name: 'Show more' }).click();
  await expect(rows).toHaveCount(50);
});

test('no figure on a card is cut off', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page.getByText('Fees collected', { exact: true })).toBeVisible();
  const clipped = await page.locator('main p.text-2xl').evaluateAll((figures) => figures.filter((figure) => figure.scrollWidth > figure.clientWidth).map((figure) => figure.textContent));
  expect(clipped).toEqual([]);
});

test('the chatbot suggests nobody by name', async ({ page }) => {
  await page.goto('/chatbot');
  await expect(page.getByRole('log')).toContainText('school assistant');
  await expect(page.locator('main')).not.toContainText('Ahmed Khan');
  await expect(page.locator('main')).not.toContainText('Bilal');
});

test('every navigation link opens its page', async ({ page }, info) => {
  await page.goto('/dashboard');
  const labels = ['Students', 'Fees', 'Exam Results', 'Academic Early Warning', 'School Assistant', 'Admissions', 'Dashboard'];
  for (const label of labels) {
    if (info.project.name === 'phone') {
      await page.getByRole('button', { name: 'Open navigation menu' }).click();
    }
    await page.locator('nav').getByRole('link', { name: label, exact: true }).click();
    await expect(page.locator('main')).toBeVisible();
    await expect(page.locator('main [role=alert]')).toHaveCount(0);
  }
});
