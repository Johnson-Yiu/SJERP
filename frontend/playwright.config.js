import { defineConfig } from '@playwright/test'

const port = Number(process.env.PLAYWRIGHT_WEB_SERVER_PORT || 5195)
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error('PLAYWRIGHT_WEB_SERVER_PORT must be a valid TCP port.')
}
const baseURL = `http://127.0.0.1:${port}`
const usePlaywrightWebServer = ['1', 'true'].includes(String(process.env.CI || '').toLowerCase())
const webServer = usePlaywrightWebServer
  ? {
      command: `npm run dev -- --port ${port} --host 127.0.0.1`,
      url: baseURL,
      reuseExistingServer: false,
    }
  : undefined

export default defineConfig({
  testDir: './browser-tests',
  use: { baseURL, browserName: 'chromium', channel: process.env.PLAYWRIGHT_CHANNEL || undefined },
  ...(webServer ? { webServer } : {}),
})
