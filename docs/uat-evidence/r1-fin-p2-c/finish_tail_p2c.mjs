import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import playwright from '../../../frontend/node_modules/playwright/index.js'
const { chromium } = playwright
const out = fileURLToPath(new URL('.', import.meta.url))
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await context.newPage()
page.setDefaultTimeout(15000)
const observations = []
page.on('response', async response => {
  const url = new URL(response.url())
  if (!url.pathname.startsWith('/api/rmb-cash-events')) return
  let body = null
  try { body = await response.json() } catch {}
  observations.push({ method: response.request().method(), path: url.pathname, status: response.status(), body })
})
async function shot(name) { await page.screenshot({ path: path.join(out, name.endsWith('.png') ? name : `${name}.png`), fullPage: true }) }
await page.goto('http://127.0.0.1:5213/rmb-cash-events', { waitUntil: 'networkidle' })
await page.getByRole('button', { name: '新建资金事件' }).click()
await page.getByLabel('银行净额（CNY）').fill('87.60')
await page.getByLabel('参考折算汇率').fill('7.100000')
await page.getByLabel('来源银行账户标识').fill('SYNTH-FX-02')
await page.getByLabel('人民币账户标识').fill('SYNTH-CNY-02')
await page.getByLabel('银行参考号').fill('P2C-BANK-H')
await page.getByLabel('凭证引用').fill('synthetic-bank-voucher.json')
await page.getByLabel('凭证 SHA256').fill('89a84663e486a3a14a6ece97bc2ac9038703e60aeaa4189f302f6264a79519fc')
await page.getByLabel('人工核实说明').fill('隔离合成凭证，已核对历史四位小数来源，按USD两位本次分配')
await page.locator('.source-toolbar input').fill('P2C-USD-HIST-4DP')
await page.locator('.source-option').filter({ hasText: 'P2C-USD-HIST-4DP' }).getByRole('button', { name: '选择', exact: true }).click()
const row = page.locator('.allocation-table tbody tr').filter({ hasText: 'P2C-USD-HIST-4DP' })
await row.locator('input[type="number"]').fill('12.34')
await row.locator('.verification-toggle input').check()
await page.getByRole('button', { name: '后端预览' }).click()
await page.locator('.preview-box').waitFor()
await shot('h-historical-4dp-preview-1440.png')
await page.getByRole('button', { name: '登记待确认草稿' }).click()
await page.getByRole('heading', { name: '资金事件待确认' }).waitFor()
await shot('h-historical-4dp-pending-1440.png')
await page.getByRole('button', { name: '放弃草稿' }).click()
await page.getByLabel('放弃原因').fill('P2-C 隔离验收：保留历史四位小数来源，暂不确认银行事实')
await page.getByRole('button', { name: '确认放弃草稿' }).click()
await page.getByText('待确认草稿已留痕放弃').waitFor()
await shot('h-historical-4dp-cancelled-1440.png')
for (const [width, height] of [[1280, 800], [1024, 768]]) {
  await page.setViewportSize({ width, height })
  await page.reload({ waitUntil: 'networkidle' })
  await shot(`list-${width}`)
}
await fs.writeFile(path.join(out, 'tail-http.json'), JSON.stringify(observations, null, 2), 'utf8')
await browser.close()
console.log(JSON.stringify({ REAL_UI_ACTION: 'historical 4dp preview/register/cancel', REAL_API_OBSERVATION: observations.length }))
