import { defineConfig } from '@playwright/test'
import path from 'node:path'

const baseURL = process.env.ISOLATED_PLAYWRIGHT_BASE_URL
if (!baseURL) throw new Error('ISOLATED_PLAYWRIGHT_BASE_URL must be assigned by the isolation runner.')
const isolationRoot = process.env.ISOLATED_TEST_ROOT
if (!isolationRoot) throw new Error('ISOLATED_TEST_ROOT must be assigned by the isolation runner.')
const businessTest = process.env.ISOLATED_PLAYWRIGHT_TEST_FILE || ''
const businessSuite = businessTest === '*'
const codexStorageState = process.env.ISOLATED_CODEX_TEST_SUPERADMIN === '1'
  ? path.join(path.resolve(isolationRoot), 'codex-auth.json')
  : undefined
const excludedBusinessTests = process.env.ISOLATED_PLAYWRIGHT_TEST_EXCLUDE
  ? JSON.parse(process.env.ISOLATED_PLAYWRIGHT_TEST_EXCLUDE)
  : []
if (!Array.isArray(excludedBusinessTests) || excludedBusinessTests.some(name => typeof name !== 'string' || !name.endsWith('.spec.js'))) {
  throw new Error('ISOLATED_PLAYWRIGHT_TEST_EXCLUDE must be a JSON array of business test filenames.')
}
if (businessTest && !businessSuite && (businessTest.includes('/') || businessTest.includes('\\') || !businessTest.endsWith('.spec.js'))) {
  throw new Error('ISOLATED_PLAYWRIGHT_TEST_FILE must be a validated .spec.js filename from the isolated runner.')
}

export default defineConfig({
  ...(codexStorageState ? { globalSetup: './browser-tests/helpers/codex-auth.global-setup.js' } : {}),
  testDir: businessTest ? './browser-tests' : './infrastructure-tests',
  testMatch: businessSuite ? '**/*.spec.js' : businessTest || '**/*.spec.js',
  testIgnore: excludedBusinessTests.map(name => `**/${name}`),
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: 'list',
  outputDir: path.resolve(process.env.ISOLATED_PLAYWRIGHT_OUTPUT_DIR || path.join(path.resolve(isolationRoot), 'playwright-results')),
  use: {
    baseURL,
    browserName: 'chromium',
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
    ...(codexStorageState ? { storageState: codexStorageState } : {}),
  },
})
