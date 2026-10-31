import { chromium } from '../../../frontend/node_modules/playwright/index.mjs'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

const root = path.resolve(decodeURIComponent(new URL('.', import.meta.url).pathname.slice(1)))
const screenshots = path.join(root, 'screenshots')
await mkdir(screenshots, { recursive: true })
const network = []
const browser = await chromium.launch({ channel: 'chrome', headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  page.on('console', message => console.log(`browser console ${message.type()}: ${message.text()}`))
  page.on('pageerror', error => console.log(`browser pageerror: ${error.stack || error.message}`))
  page.on('response', response => {
    if (response.status() >= 400) console.log(`browser response ${response.status()} ${response.url()}`)
    if (new URL(response.url()).pathname.startsWith('/api/')) {
      network.push({ method: response.request().method(), url: response.url(), status: response.status() })
    }
  })

  await page.goto('http://127.0.0.1:5297/purchase-orders?detail=1', { waitUntil: 'networkidle' })
  console.log('purchase body:', (await page.locator('body').innerText()).slice(0, 1000))
  await page.getByRole('dialog', { name: '采购工作台' }).waitFor()
  await page.screenshot({ path: path.join(screenshots, 'chrome-purchase-workbench-desktop.png'), fullPage: true })
  await page.getByRole('button', { name: '收货', exact: true }).click()
  await page.getByRole('button', { name: '验货入库', exact: true }).waitFor()
  await page.screenshot({ path: path.join(screenshots, 'chrome-purchase-receipt-desktop.png'), fullPage: true })

  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: path.join(screenshots, 'chrome-purchase-receipt-narrow.png'), fullPage: true })

  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('http://127.0.0.1:5297/orders?detail=1&tab=fulfillment', { waitUntil: 'networkidle' })
  await page.getByRole('dialog', { name: '订单工作台' }).waitFor()
  await page.getByRole('button', { name: '采购与发货', exact: true }).click()
  await page.getByText('发货记录', { exact: true }).waitFor()
  await page.screenshot({ path: path.join(screenshots, 'chrome-order-fulfillment-desktop.png'), fullPage: true })

  await page.goto('http://127.0.0.1:5297/inventory', { waitUntil: 'networkidle' })
  await page.locator('.inventory-row').first().waitFor()
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: path.join(screenshots, 'chrome-inventory-narrow.png'), fullPage: true })
  await writeFile(path.join(root, 'browser-network.json'), JSON.stringify(network, null, 2), 'utf8')
  console.log(JSON.stringify({ screenshots, networkRequests: network.length }, null, 2))
} finally {
  await browser.close()
}
