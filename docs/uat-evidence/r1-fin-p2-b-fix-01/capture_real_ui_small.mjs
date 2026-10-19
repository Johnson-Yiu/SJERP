import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import playwright from '../../../frontend/node_modules/playwright/index.js'

const { chromium } = playwright
const evidencePath = fileURLToPath(new URL('.', import.meta.url))
const browser = await chromium.launch({ headless: true })
const requestLog = []
for (const [width, height] of [[1280, 800], [1024, 768]]) {
  const context = await browser.newContext({ viewport: { width, height } })
  const page = await context.newPage()
  page.on('response', response => {
    const url = new URL(response.url())
    if (url.pathname.startsWith('/api/rmb-cash-events')) requestLog.push({ viewport: width, method: response.request().method(), path: url.pathname, status: response.status() })
  })
  await page.goto('http://127.0.0.1:5212/rmb-cash-events', { waitUntil: 'networkidle' })
  await page.screenshot({ path: path.join(evidencePath, `real-ui-list-${width}.png`), fullPage: true })
  await page.getByRole('button', { name: '查看详情' }).first().click()
  await page.locator('.cash-detail-panel').waitFor()
  await page.screenshot({ path: path.join(evidencePath, `real-ui-detail-${width}.png`), fullPage: true })
  await context.close()
}
await fs.writeFile(path.join(evidencePath, 'real-ui-http-small.json'), JSON.stringify(requestLog, null, 2), 'utf8')
console.log(JSON.stringify({ viewports: [1280, 1024], requests: requestLog.length }))
await browser.close()
