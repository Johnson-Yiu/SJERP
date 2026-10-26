import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './browser-tests',
  testMatch: 'iss022-moq-real.spec.js',
  use: {
    baseURL: 'http://127.0.0.1:54128',
    browserName: 'chromium',
    channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome',
    trace: 'retain-on-failure',
  },
  reporter: [['list'], ['json', { outputFile: process.env.ISS022_EVIDENCE_DIR ? `${process.env.ISS022_EVIDENCE_DIR}/playwright-report.json` : 'test-results/iss022-playwright.json' }]],
  webServer: {
    command: 'npm run dev -- --config vite.iss022.config.js --port 54128 --host 127.0.0.1',
    url: 'http://127.0.0.1:54128',
    reuseExistingServer: false,
  },
})
