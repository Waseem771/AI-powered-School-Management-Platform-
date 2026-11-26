// The shared demo login in the full-access online demo: it creates and removes accounts, and talks to no other backend.
import { expect, test } from '@playwright/test';
import { API_PORT, E2E_PASSWORD } from '../playwright.config.js';
import { dialog, watchForProblems } from './helpers.js';

test('the demo login manages parent and teacher accounts, using only its own backend', async ({ page }) => {
  const problems = watchForProblems(page);
  const hosts = new Set();
  page.on('request', (request) => {
    if (['fetch', 'xhr'].includes(request.resourceType())) hosts.add(new URL(request.url()).host);
  });

  await page.goto('/login');
  await page.getByLabel('Username').fill('demo');
  await page.getByLabel('Password').fill(E2E_PASSWORD);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByText('DEMO MODE', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Change Password' })).toHaveCount(0);

  // Parent: create (the screen that used to refuse), then delete.
  await page.goto('/parents');
  await page.getByRole('button', { name: 'Add Parent' }).click();
  await dialog(page).getByLabel('Full name').fill('Synthetic Parent');
  await dialog(page).getByLabel('Username').fill('synthetic.parent');
  await dialog(page).getByLabel('Initial password').fill('a-long-password-1');
  await dialog(page).getByRole('combobox', { name: 'Add a child' }).fill('a');
  await page.getByRole('listbox').getByRole('option').first().click();
  await dialog(page).getByRole('button', { name: 'Create Account' }).click();
  await expect(page.getByText('Account created for Synthetic Parent.')).toBeVisible();
  await page.getByRole('button', { name: 'Delete Synthetic Parent' }).click();
  await dialog(page).getByRole('button', { name: 'Delete account' }).click();
  await expect(page.getByText("Synthetic Parent's account was deleted.")).toBeVisible();
  await expect(page.getByText('synthetic.parent')).toHaveCount(0);

  // Teacher: create, deactivate, delete.
  await page.goto('/teachers');
  await page.getByRole('button', { name: 'Add Teacher' }).click();
  await dialog(page).getByLabel('Full name').fill('Synthetic Teacher');
  await dialog(page).getByLabel('Username').fill('synthetic.teacher');
  await dialog(page).getByLabel('Initial password').fill('a-long-password-1');
  await dialog(page).getByRole('button', { name: 'Create Account' }).click();
  await expect(page.getByText('Account created for Synthetic Teacher.')).toBeVisible();
  await page.getByRole('button', { name: 'Deactivate Synthetic Teacher' }).click();
  await dialog(page).getByRole('button', { name: 'Deactivate' }).click();
  await expect(page.getByText('Synthetic Teacher is now deactivated.')).toBeVisible();
  await page.getByRole('button', { name: 'Delete Synthetic Teacher' }).click();
  await dialog(page).getByRole('button', { name: 'Delete account' }).click();
  await expect(page.getByText("Synthetic Teacher's account was deleted.")).toBeVisible();

  await expect(page.getByText('cannot remove anything')).toHaveCount(0);
  expect([...hosts]).toEqual([`localhost:${API_PORT}`]);
  expect(problems).toEqual([]);
});
