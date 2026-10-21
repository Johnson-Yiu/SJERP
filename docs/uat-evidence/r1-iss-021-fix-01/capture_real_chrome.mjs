import { chromium } from '../../../frontend/node_modules/playwright/index.mjs'
import { mkdir } from 'node:fs/promises'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('.', import.meta.url))
await mkdir(root, { recursive: true })

// The channel is the installed Google Chrome, not Playwright's bundled Chromium.
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const results = []

for (const width of [1440, 1024, 700]) {
  const page = await browser.newPage({ viewport: { width, height: 1000 } })
  await page.goto('http://127.0.0.1:5173/orders', { waitUntil: 'networkidle' })
  await page.getByText('SO-UAT-021', { exact: true }).first().click()
  await page.getByRole('button', { name: '调整数量', exact: true }).click()
  const quantity = page.getByRole('spinbutton', { name: '新的基础数量 UAT-SKU-021', exact: true })
  const reason = page.getByRole('textbox', { name: '变更原因', exact: true })
  if (width === 700) {
    await quantity.fill('60')
    await reason.fill('FIX-01 真实 Chrome 已发货下限验证')
  } else {
    await quantity.fill('120')
    await reason.fill('FIX-01 真实 Chrome 合法变更预览')
  }
  await page.getByRole('button', { name: '预览影响', exact: true }).click()
  await page.waitForTimeout(250)
  const body = await page.locator('body').innerText()
  const expected = width === 700 ? '不能低于已发货数量 70' : '120.00'
  if (!body.includes(expected)) throw new Error(`${width}px 未找到预期内容：${expected}`)
  const filename = `real-chrome-quantity-adjustment-${width}.png`
  await page.screenshot({ path: join(root, filename), fullPage: false })
  results.push({ width, filename, expected })
  await page.getByRole('button', { name: '取消', exact: true }).click()
  await page.close()
}

const page = await browser.newPage({ viewport: { width: 700, height: 1000 } })
await page.goto('http://127.0.0.1:5173/orders', { waitUntil: 'networkidle' })
await page.getByText('SO-UAT-021', { exact: true }).first().click()
await page.getByRole('button', { name: '调整数量', exact: true }).click()
const currentQuantity = page.getByRole('spinbutton', { name: '新的基础数量 UAT-SKU-021', exact: true })
await currentQuantity.fill('150')
await page.getByRole('textbox', { name: '变更原因', exact: true }).fill('FIX-01 真实 Chrome 空变更验证')
const noopBody = await page.locator('body').innerText()
if (!noopBody.includes('数量没有变化')) throw new Error('700px 未显示空变更提示')
if (await page.getByRole('button', { name: '预览影响', exact: true }).isEnabled()) throw new Error('空变更按钮不应可用')
await page.screenshot({ path: join(root, 'real-chrome-quantity-adjustment-noop-700.png'), fullPage: false })
results.push({ width: 700, filename: 'real-chrome-quantity-adjustment-noop-700.png', expected: '数量没有变化' })
await page.close()

await browser.close()
console.log(JSON.stringify({ results }, null, 2))
