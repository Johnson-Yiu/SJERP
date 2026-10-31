import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './browser-tests',
  testMatch: 'iss075-payment-terms-real.spec.js',
  use: {
    baseURL: 'http://127.0.0.1:54175',
    browserName: 'chromium',
    channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome',
    trace: 'retain-on-failure',
  },
  reporter: [['list'], ['json', { outputFile: process.env.ISS075_EVIDENCE_DIR ? `${process.env.ISS075_EVIDENCE_DIR}/playwright-report.json` : 'test-results/iss075-playwright.json' }]],
  webServer: {
    command: 'npm run dev -- --config vite.iss075.config.js --port 54175 --host 127.0.0.1',
    url: 'http://127.0.0.1:54175',
    reuseExistingServer: false,
  },
})
