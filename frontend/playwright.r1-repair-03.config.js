import { defineConfig } from '@playwright/test'

const apiPort = process.env.R1_REPAIR_API_PROXY_PORT || '8303'
const frontendPort = process.env.R1_REPAIR_FRONTEND_PORT || '5197'

export default defineConfig({
  testDir: './browser-tests',
  testMatch: /(?:historical-orders-fix-02|historical-orders-fix-03|iss029-recipient-snapshot)\.spec\.js/,
  timeout: 120000,
  workers: 1,
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    browserName: 'chromium',
    channel: 'chrome',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
    url: `http://127.0.0.1:${frontendPort}`,
    reuseExistingServer: false,
    env: { VITE_API_PROXY_PORT: apiPort },
  },
})
