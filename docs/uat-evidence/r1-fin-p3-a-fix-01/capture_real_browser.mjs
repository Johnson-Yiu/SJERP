import { chromium } from '../../../frontend/node_modules/@playwright/test/index.mjs'
import { writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { join } from 'node:path'

const root = fileURLToPath(new URL('.', import.meta.url))
const log = []
const browser = await chromium.launch()
for (const width of [1440, 1280, 1024]) {
  const page = await browser.newPage({ viewport: { width, height: 1000 } })
  page.on('response', response => {
    const url = response.url()
    if (url.includes('/api/finance-dashboard/') || url.includes('/api/actual-rmb-cash/')) log.push(`${width} ${response.status()} ${url}`)
  })
  await page.goto('http://127.0.0.1:5194/finance?date_from=2026-10-01&date_to=2026-10-19', { waitUntil: 'networkidle' })
  await page.getByRole('heading', { name: '银行实际人民币资金', exact: true }).waitFor()
  await page.getByText('¥705.00', { exact: true }).first().waitFor()
  await page.screenshot({ path: join(root, `real-browser-finance-${width}.png`), fullPage: true })
  log.push(`${width} visible actual cash: ${JSON.stringify((await page.locator('.actual-cash-section').innerText()).replace(/\s+/g, ' ').trim())}`)
  await page.close()
}
await writeFile(join(root, 'real-browser-http.log'), `${log.join('\n')}\n`, 'utf8')
await browser.close()
