import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './browser-tests', testMatch: 'iss029-recipient-snapshot.spec.js',
  timeout: 120000, workers: 1,
  use: { baseURL: 'http://127.0.0.1:5299', browserName: 'chromium', channel: 'chrome' },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5299',
    url: 'http://127.0.0.1:5299', reuseExistingServer: false,
    env: { VITE_API_PROXY_PORT: '8299' },
  },
})
