import { defineConfig } from '@playwright/test'
import path from 'node:path'

const baseURL = process.env.ISOLATED_PLAYWRIGHT_BASE_URL
if (!baseURL) throw new Error('ISOLATED_PLAYWRIGHT_BASE_URL must be assigned by the isolation runner.')
const isolationRoot = process.env.ISOLATED_TEST_ROOT
if (!isolationRoot) throw new Error('ISOLATED_TEST_ROOT must be assigned by the isolation runner.')
const businessTest = process.env.ISOLATED_PLAYWRIGHT_TEST_FILE || ''
if (businessTest && (businessTest.includes('/') || businessTest.includes('\\') || !businessTest.endsWith('.spec.js'))) {
  throw new Error('ISOLATED_PLAYWRIGHT_TEST_FILE must be a validated .spec.js filename from the isolated runner.')
}

export default defineConfig({
  testDir: businessTest ? './browser-tests' : './infrastructure-tests',
  testMatch: businessTest || '**/*.spec.js',
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: 'list',
  outputDir: path.join(path.resolve(isolationRoot), 'playwright-results'),
  use: {
    baseURL,
    browserName: 'chromium',
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
  },
})
