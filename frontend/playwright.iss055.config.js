import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './browser-tests',
  testMatch: 'iss055-customer-404-real.spec.js',
  use: {
    baseURL: 'http://127.0.0.1:55155',
    browserName: 'chromium',
    channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome',
    trace: 'retain-on-failure',
  },
  reporter: [['list'], ['json', { outputFile: process.env.ISS055_EVIDENCE_DIR ? `${process.env.ISS055_EVIDENCE_DIR}/playwright-report.json` : 'test-results/iss055-playwright.json' }]],
  webServer: {
    command: 'npm run dev -- --port 55155 --host 127.0.0.1',
    url: 'http://127.0.0.1:55155',
    reuseExistingServer: false,
  },
})
