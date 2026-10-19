import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import playwright from '../../../frontend/node_modules/playwright/index.js'

const { chromium } = playwright
const evidencePath = fileURLToPath(new URL('.', import.meta.url))
const base = 'http://127.0.0.1:5212/rmb-cash-events'
const requests = []
const browser = await chromium.launch({ headless: true })

async function screenshot(page, name) {
  await page.screenshot({ path: path.join(evidencePath, name), fullPage: true })
}

async function fillFacts(page, bankNet = '705.00') {
  await page.getByLabel('银行净额（CNY）').fill(bankNet)
  await page.getByLabel('参考折算汇率').fill('7.100000')
  await page.getByLabel('来源银行账户标识').fill('SYNTH-FX-01')
  await page.getByLabel('人民币账户标识').fill('SYNTH-CNY-01')
  await page.getByLabel('银行参考号').fill(`P2B-FIX-02-${bankNet.replace('.', '-')}`)
  await page.getByLabel('凭证引用').fill('synthetic-bank-voucher.json')
  await page.getByLabel('凭证 SHA256').fill('a'.repeat(64))
  await page.getByLabel('人工核实说明').fill('隔离合成凭证，已核对银行日期、净额和来源分配')
}

const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await context.newPage()
page.on('response', response => {
  const url = new URL(response.url())
  if (url.pathname.startsWith('/api/rmb-cash-events')) requests.push({ method: response.request().method(), path: url.pathname, status: response.status() })
})

await page.goto(base, { waitUntil: 'networkidle' })
await page.getByRole('button', { name: '新建资金事件' }).click()
await fillFacts(page)
const source = page.locator('.source-option').nth(1)
await source.getByRole('button', { name: '选择' }).click()
await page.locator('.allocation-table input[type="number"]').fill('30')
await screenshot(page, 'real-ui-source-30-selected-1440.png')
await page.locator('.verification-toggle input').check()
await page.getByRole('button', { name: '后端预览' }).click()
await page.locator('.preview-box').waitFor()
await screenshot(page, 'real-ui-preview-30-1440.png')
await page.locator('.allocation-table input[type="number"]').fill('50')
await page.getByText('旧预览已失效').waitFor()
await screenshot(page, 'real-ui-allocation-50-pending-1440.png')
await page.locator('.verification-toggle input').check()
await page.getByRole('button', { name: '后端预览' }).click()
await page.locator('.preview-box').waitFor()
await screenshot(page, 'real-ui-preview-50-1440.png')

await page.reload({ waitUntil: 'networkidle' })
await page.getByRole('button', { name: '新建资金事件' }).click()
await page.getByText('已恢复未完成草稿').waitFor()
await screenshot(page, 'real-ui-restored-draft-1440.png')
await page.getByRole('button', { name: '取消', exact: true }).click()
await page.getByRole('heading', { name: '未保存修改', exact: true }).waitFor()
await screenshot(page, 'real-ui-restored-close-prompt-1440.png')
await page.getByRole('button', { name: '继续编辑', exact: true }).click()
await screenshot(page, 'real-ui-restored-cancelled-close-1440.png')
await page.getByRole('button', { name: '取消', exact: true }).click()
await page.getByRole('button', { name: '放弃修改', exact: true }).click()
await page.getByRole('button', { name: '新建资金事件' }).click()
await screenshot(page, 'real-ui-after-explicit-abandon-1440.png')

for (const [width, height] of [[1280, 800], [1024, 768]]) {
  await page.setViewportSize({ width, height })
  await page.reload({ waitUntil: 'networkidle' })
  await screenshot(page, `real-ui-list-${width}.png`)
}

await fs.writeFile(path.join(evidencePath, 'real-ui-http.json'), JSON.stringify(requests, null, 2), 'utf8')
await fs.writeFile(path.join(evidencePath, 'local-storage-policy.json'), JSON.stringify({
  storage_key: 'sunjack:r1-fin-p2-b:cash-event-draft:v1',
  expiry_hours: 24,
  persisted_form_fields: ['event_no', 'request_key', 'kind', 'currency', 'direction', 'bank_date', 'bank_net_amount', 'fee_mode', 'fee_amount', 'source_account', 'rmb_account', 'bank_reference', 'quoted_rate', 'fee_for'],
  omitted_fields: ['evidence_reference', 'evidence_sha256', 'evidence_note'],
  sensitive_fields_reentered_after_restore: true,
}, null, 2), 'utf8')
await context.close()
await browser.close()
console.log(JSON.stringify({ screenshots: 9, requests: requests.length }))
