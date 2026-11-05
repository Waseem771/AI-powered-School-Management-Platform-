import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from '@playwright/test';

// Runs the production build against a throwaway demo database, on its own ports, so it can run
// while the app is open for other use. Set E2E_PYTHON if `python` lacks the backend's packages.
const python = process.env.E2E_PYTHON || 'python';
const browserChannel = process.env.E2E_CHANNEL || 'msedge';
const here = path.dirname(fileURLToPath(import.meta.url));
const dataFolder = path.join(os.tmpdir(), 'educore_e2e');
fs.mkdirSync(dataFolder, { recursive: true });
const database = path.join(dataFolder, 'demo_e2e.db');

export const API_PORT = 8010;
export const WEB_PORT = 5183;
export const E2E_PASSWORD = 'e2e-only-demo-password-1';

const backendEnv = {
  APP_ENV: 'development',
  DEMO_MODE: 'true',
  DATABASE_URL: `sqlite:///${database.replaceAll('\\', '/')}`,
  DEMO_ADMIN_PASSWORD: E2E_PASSWORD,
  FRONTEND_URL: `http://localhost:${WEB_PORT}`,
  GROQ_API_KEY: '',
  SCHOOL_NAME: 'Roshan Demo Academy',
  SCHOOL_ADDRESS: 'Demo Road, Khairpur, Sindh',
  SCHOOL_PHONE: '0999-0000000',
  PYTHONDONTWRITEBYTECODE: '1',
  PYTHONIOENCODING: 'utf-8',
  PYTHONWARNINGS: 'ignore',
};

export default defineConfig({
  testDir: './e2e',
  outputDir: './test-results',
  fullyParallel: false,
  workers: 1,
  timeout: 180_000,
  expect: { timeout: 15_000 },
  reporter: [['list']],
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    channel: browserChannel,
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1280, height: 800 } } },
    { name: 'tablet', testMatch: /responsive/, use: { viewport: { width: 768, height: 1024 }, hasTouch: true } },
    { name: 'phone', testMatch: /responsive/, use: { viewport: { width: 375, height: 812 }, hasTouch: true, isMobile: true } },
  ],
  webServer: [
    {
      command: `"${python}" seed_demo.py --output "${database}" --replace && "${python}" -m uvicorn main:app --port ${API_PORT}`,
      cwd: path.join(here, '..', 'backend'),
      url: `http://localhost:${API_PORT}/school/public`,
      env: backendEnv,
      timeout: 180_000,
      reuseExistingServer: false,
    },
    {
      command: `npm run build && npx vite preview --port ${WEB_PORT} --strictPort`,
      cwd: here,
      url: `http://localhost:${WEB_PORT}`,
      env: { VITE_API_URL: `http://localhost:${API_PORT}`, E2E_API_ORIGIN: `http://localhost:${API_PORT}` },
      timeout: 180_000,
      reuseExistingServer: false,
    },
  ],
});
