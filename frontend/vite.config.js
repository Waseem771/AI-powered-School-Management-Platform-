import fs from 'node:fs';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/** The headers Vercel will send, so the production build can be tested with them. */
function productionHeaders() {
  const { headers } = JSON.parse(fs.readFileSync(new URL('./vercel.json', import.meta.url), 'utf-8'));
  const extraApiOrigin = process.env.E2E_API_ORIGIN;
  return Object.fromEntries(headers[0].headers.map(({ key, value }) => [
    key,
    extraApiOrigin ? value.replace("connect-src 'self'", `connect-src 'self' ${extraApiOrigin}`) : value,
  ]));
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true
  },
  preview: {
    headers: productionHeaders()
  }
});
