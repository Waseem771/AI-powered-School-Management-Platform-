// The 10-minute talk in SAMPLE_DEMO_SCENARIO.md, step by step, as a person would click it.
import { expect, test } from '@playwright/test';
import { dialog, expectPdfOpens, signIn, watchForProblems } from './helpers.js';



test('the whole demo works from sign-in to the School Assistant', async ({ page }) => {
  const problems = watchForProblems(page);

  await test.step('1. sign in, with a refusal first', async () => {
    await page.goto('/login');
    await expect(page.getByText('Simple School Management, Smarter Decisions')).toBeVisible();
    await expect(page.getByText('Roshan Demo Academy')).toBeVisible();
    await expect(page.getByText('DEMO MODE: made-up records')).toBeVisible();
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page.getByRole('alert')).toContainText('Enter your username and password');
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('not-the-password');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page.getByRole('alert')).toContainText('Incorrect');
    await signIn(page);
  });

  await test.step('2. dashboard, month filter, and recent activity', async () => {
    await expect(page.getByText('Current students', { exact: true })).toBeVisible();
    await expect(page.getByText('119', { exact: true })).toBeVisible();
    await page.getByLabel('Fees shown for').selectOption({ index: 2 });
    await expect(page.getByText(/^Collected for /)).toBeVisible();
    await page.getByLabel('Fees shown for').selectOption({ index: 0 });
    await expect(page.getByText('Fees collected', { exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Recent activity' })).toBeVisible();
    await expect(page.getByText(/received for /).first()).toBeVisible();
  });

  await test.step('3. find a student and open the profile', async () => {
    await page.getByRole('link', { name: 'Students', exact: true }).first().click();
    await page.getByRole('group', { name: 'Grade' }).getByRole('button', { name: 'Grade 8' }).click();
    await page.getByRole('group', { name: 'Section' }).getByRole('button', { name: 'Section A' }).click();
    await page.getByRole('searchbox').fill('Hina');
    await page.locator('a:visible', { hasText: 'Hina Soomro' }).click();
    await expect(page.getByRole('heading', { name: 'Hina Soomro' })).toBeVisible();
    await expect(page.getByText('Roll #801')).toBeVisible();
  });

  const partPaidRow = page.locator('tbody tr', { hasText: 'Part Paid' });

  await test.step('4. payment history, a refused amount, payment, and receipt', async () => {
    await partPaidRow.getByRole('button', { name: 'Payments' }).click();
    await expect(dialog(page).getByText('RCP-').first()).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(dialog(page)).toHaveCount(0);

    await partPaidRow.getByRole('button', { name: 'Record Payment' }).click();
    await dialog(page).getByLabel('Amount received').fill('999999');
    await dialog(page).getByRole('button', { name: 'Confirm Payment' }).click();
    await expect(dialog(page).getByRole('alert')).toContainText('more than');
    await dialog(page).getByLabel('Amount received').fill('2000');
    await dialog(page).getByRole('button', { name: 'Confirm Payment' }).click();
    await expect(dialog(page).getByRole('heading', { name: 'Payment Recorded' })).toBeVisible();
    await expectPdfOpens(page, () => dialog(page).getByRole('button', { name: 'Print Receipt' }).click());
    await dialog(page).getByRole('button', { name: 'Done' }).click();
    await expect(page.getByText('Still owed').locator('..').getByText('Rs. 0')).toBeVisible();
  });

  await test.step('5. challan PDF', async () => {
    await expectPdfOpens(page, () => page.locator('tbody tr').first().getByRole('button', { name: 'Challan' }).click());
  });

  await test.step('6. whole-class marks, with a refused mark', async () => {
    await page.getByRole('link', { name: 'Exam Results' }).first().click();
    await page.getByRole('button', { name: 'Enter for a Class' }).click();
    const sheet = dialog(page);
    await sheet.getByLabel('Grade').selectOption('Grade 8');
    await sheet.getByLabel('Section').selectOption('A');
    await sheet.getByLabel('Subject').selectOption('Science');
    await sheet.getByLabel('Exam').selectOption('Final Term');
    const marks = sheet.locator('li input');
    await expect(marks).toHaveCount(12);
    await marks.first().fill('150');
    await sheet.getByRole('button', { name: /^Save/ }).click();
    await expect(sheet.getByRole('alert')).toContainText('Nothing has been saved');
    await marks.first().fill('83');
    await sheet.getByRole('button', { name: /^Save/ }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Science marks saved' })).toBeVisible();
  });

  await test.step('7. report card', async () => {
    await page.getByRole('combobox').fill('Hina');
    await page.getByRole('option', { name: /Hina Soomro/ }).click();
    await expect(page.getByRole('cell', { name: 'Science' })).toBeVisible();
    await expect(page.getByRole('cell', { name: '83 of 100' })).toBeVisible();
    await expectPdfOpens(page, () => page.getByRole('button', { name: 'Report Card' }).click());
  });

  await test.step('8. early warning: a real fall, fees kept apart, and no invented score', async () => {
    await page.getByRole('link', { name: 'Academic Early Warning' }).first().click();
    await expect(page.getByText('Trained on synthetic data')).toBeVisible();
    const search = page.getByRole('searchbox');

    await search.fill('Danish Memon');
    await expect(page.getByText('High estimate')).toBeVisible();
    await page.getByRole('button', { name: 'Why and what next' }).click();
    await expect(dialog(page).getByText(/fell 21\.5 points/)).toBeVisible();
    await page.keyboard.press('Escape');

    await search.fill('Maham Shaikh');
    await expect(page.getByText('Low estimate')).toBeVisible();
    await expect(page.getByText(/Fee follow-up/)).toBeVisible();

    await search.fill('Kiran Mangi');
    await expect(page.getByText('No score')).toHaveCount(0);
    await expect(page.locator('span', { hasText: /^Not enough data$/ })).toBeVisible();

    await page.getByRole('button', { name: 'Try the model' }).click();
    await expect(dialog(page).getByText(/Score \d+ of 100/)).toBeVisible();
    await page.keyboard.press('Escape');
  });

  await test.step('9. School Assistant', async () => {
    await page.getByRole('link', { name: 'School Assistant' }).first().click();
    const ask = async (question, expected) => {
      await page.getByPlaceholder(/Ask about students/).fill(question);
      await page.getByRole('button', { name: 'Send' }).click();
      await expect(page.getByRole('log').getByText(expected).last()).toBeVisible({ timeout: 120_000 });
    };
    await ask('Fees of Ali Junejo', 'Which student do you mean?');
    await ask('1051', /roll #1051, Grade 10-B/);
    await ask('How many students are there?', /119 current student/);
    await ask('What is the fee refund policy?', 'From policy documents');
    await ask('What is the capital of France?', /cannot answer that/);
  });

  expect(problems).toEqual([]);
});

test('signing out ends the session and clears saved data', async ({ page }) => {
  await signIn(page);
  await page.getByRole('button', { name: 'Sign Out' }).click();
  await expect(page).toHaveURL(/\/login/);
  expect(await page.evaluate(() => Object.keys(localStorage).filter((key) => key.startsWith('educore_')))).toEqual([]);
  await page.goto('/students');
  await expect(page).toHaveURL(/\/login/);
});

test('an expired session returns to sign-in', async ({ page }) => {
  await signIn(page);
  await page.evaluate(() => localStorage.setItem('educore_token', 'no-longer-valid'));
  await page.goto('/students');
  await expect(page).toHaveURL(/\/login/, { timeout: 15_000 });
});

test('an archived student leaves the list and can return', async ({ page }) => {
  await signIn(page);
  await page.goto('/students');
  await page.getByRole('button', { name: 'Add Student' }).click();
  await dialog(page).getByLabel('Full name').fill('Playwright Student');
  await dialog(page).getByLabel('Roll number').fill('E2E-1');
  await dialog(page).getByLabel('Guardian name').fill('Playwright Guardian');
  await dialog(page).getByLabel('Contact phone').fill('0999-1234567');
  await dialog(page).getByRole('button', { name: 'Save Student' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'was added' })).toBeVisible();

  await page.getByRole('searchbox').fill('Playwright Student');
  await page.getByRole('button', { name: 'Archive Playwright Student' }).click();
  await dialog(page).getByRole('button', { name: 'Archive Student' }).click();
  await expect(page.getByText('No students match')).toBeVisible();

  await page.getByRole('button', { name: 'Archived' }).click();
  await page.getByRole('button', { name: 'Restore Playwright Student' }).click();
  await dialog(page).getByRole('button', { name: 'Restore Student' }).click();
  await page.getByRole('button', { name: 'Current Students' }).click();
  await page.getByRole('button', { name: 'Archive Playwright Student' }).click();
  await dialog(page).getByRole('button', { name: 'Archive Student' }).click();
  await page.getByRole('button', { name: 'Archived' }).click();
  await page.getByRole('button', { name: 'Delete Playwright Student permanently' }).click();
  await dialog(page).getByRole('button', { name: 'Delete Permanently' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'was deleted' })).toBeVisible();
});

test('dialogs keep keyboard focus inside and give it back', async ({ page }) => {
  await signIn(page);
  await page.goto('/fees');
  const opener = page.getByRole('button', { name: 'Issue Challan' });
  await opener.click();
  for (let press = 0; press < 12; press += 1) {
    await page.keyboard.press('Tab');
    expect(await dialog(page).evaluate((panel) => panel.contains(document.activeElement))).toBe(true);
  }
  await page.keyboard.press('Escape');
  if (await dialog(page).count()) await page.keyboard.press('Escape');
  await expect(dialog(page)).toHaveCount(0);
  await expect(opener).toBeFocused();
});
