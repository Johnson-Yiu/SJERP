import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import playwright from '../../../frontend/node_modules/playwright/index.js'

const { chromium } = playwright
const base = 'http://127.0.0.1:5212/rmb-cash-events'
const evidence = new URL('.', import.meta.url)
const evidencePath = fileURLToPath(evidence)
const widths = [[1440, 900], [1280, 800], [1024, 768]]
const requestLog = []

async function shot(page, name) {
  await page.screenshot({ path: path.join(evidencePath, name), fullPage: true })
}

const browser = await chromium.launch({ headless: true })

// One complete real API flow uses the fresh P2B-FIX-T source family.
{
  const [width, height] = widths[0]
  const context = await browser.newContext({ viewport: { width, height } })
  const page = await context.newPage()
  page.on('response', response => {
    const url = new URL(response.url())
    if (url.pathname.startsWith('/api/rmb-cash-events')) requestLog.push({ state: '1440', method: response.request().method(), path: url.pathname, status: response.status() })
  })
  await page.goto(base, { waitUntil: 'networkidle' })
  await shot(page, 'real-ui-list-1440.png')
  await page.getByRole('button', { name: '新建资金事件' }).click()
  await page.getByLabel('银行净额（CNY）').fill('705.00')
  await page.getByLabel('参考折算汇率').fill('7.100000')
  await page.getByLabel('来源银行账户标识').fill('SYNTH-FX-01')
  await page.getByLabel('人民币账户标识').fill('SYNTH-CNY-01')
  await page.getByLabel('银行参考号').fill('P2B-FIX-BANK-02')
  await page.getByLabel('凭证引用').fill('synthetic-bank-voucher.json')
  await page.getByLabel('凭证 SHA256').fill('a'.repeat(64))
  await page.getByLabel('人工核实说明').fill('隔离合成凭证，已核对银行日期、净额和来源分配')
  const source = page.locator('.source-option').filter({ hasText: 'P2B-FIX-T' })
  await source.nth(0).getByRole('button', { name: '选择' }).click()
  await page.locator('.source-option').filter({ hasText: 'FIN-' }).filter({ hasText: '可用 USD 70.00' }).getByRole('button', { name: '选择' }).click()
  await page.locator('.allocation-table input[type="number"]').nth(0).fill('30.00')
  await page.locator('.allocation-table input[type="number"]').nth(1).fill('70.00')
  await shot(page, 'real-ui-source-selected-1440.png')
  await page.getByRole('button', { name: '后端预览' }).click()
  await page.getByRole('alert').waitFor()
  await shot(page, 'real-ui-verification-rejected-1440.png')
  await page.locator('.verification-toggle input').nth(0).check()
  await page.locator('.verification-toggle input').nth(1).check()
  await page.getByRole('button', { name: '后端预览' }).click()
  await page.locator('.preview-box').waitFor()
  await shot(page, 'real-ui-preview-1440.png')
  await page.getByLabel('银行净额（CNY）').fill('706.00')
  await page.getByText('旧预览已失效').waitFor()
  await shot(page, 'real-ui-preview-invalidated-1440.png')
  await page.getByLabel('银行净额（CNY）').fill('705.00')
  await page.getByRole('button', { name: '后端预览' }).click()
  await page.locator('.preview-box').waitFor()
  await page.getByRole('button', { name: '登记待确认草稿' }).click()
  await page.getByText('资金事件待确认').waitFor()
  await shot(page, 'real-ui-review-pending-1440.png')
  await page.getByRole('checkbox', { name: /我已核对以上银行凭证/ }).check()
  await page.getByRole('button', { name: '确认银行凭证' }).click()
  await page.getByText('资金事件已确认').waitFor()
  await shot(page, 'real-ui-confirmed-1440.png')
  await page.getByRole('button', { name: '关闭资金表单' }).click()
  await shot(page, 'real-ui-list-after-confirm-1440.png')
  await context.close()
}

// Read-only list/detail checks at the two smaller required viewports.
for (const [width, height] of widths.slice(1)) {
  const context = await browser.newContext({ viewport: { width, height } })
  const page = await context.newPage()
  page.on('response', response => {
    const url = new URL(response.url())
    if (url.pathname.startsWith('/api/rmb-cash-events')) requestLog.push({ state: String(width), method: response.request().method(), path: url.pathname, status: response.status() })
  })
  await page.goto(base, { waitUntil: 'networkidle' })
  await shot(page, `real-ui-list-${width}.png`)
  await page.getByRole('button', { name: '查看详情' }).first().click()
  await page.locator('.cash-detail-panel').waitFor()
  await shot(page, `real-ui-detail-${width}.png`)
  await context.close()
}

await fs.writeFile(path.join(evidencePath, 'real-ui-http.json'), JSON.stringify(requestLog, null, 2), 'utf8')
await browser.close()
console.log(JSON.stringify({ screenshots: 12, requests: requestLog.length, evidence: evidence.pathname }))
