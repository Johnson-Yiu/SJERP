import { defineConfig } from '@playwright/test'
import path from 'node:path'

const baseURL = process.env.ISS007_BASE_URL || 'http://127.0.0.1:55208'
const evidenceDir = process.env.ISS007_EVIDENCE_DIR || path.resolve(process.cwd(), '../docs/uat-evidence/r1-pre-uat-iss007-attachment-flow')

export default defineConfig({
  testDir: './browser-tests',
  testMatch: 'iss007-attachment-real.spec.js',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: path.join(evidenceDir, 'playwright-report.json') }]],
  use: {
    baseURL,
    browserName: 'chromium',
    channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome',
    trace: 'retain-on-failure',
  },
  outputDir: path.join(evidenceDir, 'playwright-results'),
})
