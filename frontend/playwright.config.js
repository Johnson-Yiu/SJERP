import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './browser-tests',
  use: { baseURL: 'http://127.0.0.1:5195', browserName: 'chromium', channel: process.env.PLAYWRIGHT_CHANNEL || undefined },
  webServer: { command: 'npm run dev -- --port 5195 --host 127.0.0.1', url: 'http://127.0.0.1:5195', reuseExistingServer: !process.env.CI },
})
