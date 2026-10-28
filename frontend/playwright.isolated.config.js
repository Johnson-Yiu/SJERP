import { defineConfig } from '@playwright/test'

const baseURL = process.env.ISOLATED_PLAYWRIGHT_BASE_URL
if (!baseURL) throw new Error('ISOLATED_PLAYWRIGHT_BASE_URL must be assigned by the isolation runner.')

export default defineConfig({
  testDir: './infrastructure-tests',
  testMatch: '**/*.spec.js',
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL,
    browserName: 'chromium',
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
  },
})
