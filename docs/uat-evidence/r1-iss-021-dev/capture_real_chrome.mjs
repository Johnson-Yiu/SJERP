import { chromium } from '../../../frontend/node_modules/playwright/index.mjs'
import { mkdir } from 'node:fs/promises'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('.', import.meta.url))
await mkdir(root, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome', headless: true })
const results = []

for (const width of [1440, 1024, 700]) {
  const page = await browser.newPage({ viewport: { width, height: 1000 } })
  await page.goto('http://127.0.0.1:5287/orders', { waitUntil: 'networkidle' })
  await page.getByText('SO-UAT-021', { exact: true }).first().click()
  await page.getByRole('button', { name: '调整数量', exact: true }).click()
  const quantity = page.getByRole('spinbutton', { name: '新的基础数量 UAT-SKU-021', exact: true })
  const reason = page.getByRole('textbox', { name: '变更原因', exact: true })
  await quantity.fill(width === 700 ? '60' : '180')
  await reason.fill(width === 700 ? '验证窄屏下限提示' : '浏览器视觉验收预览')
  await page.getByRole('button', { name: '预览影响', exact: true }).click()
  await page.waitForTimeout(250)
  const body = await page.locator('body').innerText()
  const expected = width === 700 ? '不能低于已发货数量 70' : '180.00'
  if (!body.includes(expected)) throw new Error(`${width}px 未找到预期数量变更提示：${expected}`)
  const filename = `real-chrome-quantity-adjustment-${width}.png`
  await page.screenshot({ path: join(root, filename), fullPage: false })
  results.push({ width, filename, expected })
  await page.getByRole('button', { name: '取消', exact: true }).click()
  await page.close()
}

await browser.close()
console.log(JSON.stringify({ results }, null, 2))
