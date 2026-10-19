import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import playwright from '../../../frontend/node_modules/playwright/index.js'

const { chromium } = playwright
const evidencePath = fileURLToPath(new URL('.', import.meta.url))
const base = 'http://127.0.0.1:5213/rmb-cash-events'
const observations = []
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await context.newPage()
page.setDefaultTimeout(15000)
page.on('response', async response => {
  const url = new URL(response.url())
  if (!url.pathname.startsWith('/api/rmb-cash-events')) return
  let body = null
  try { body = await response.json() } catch {}
  observations.push({ method: response.request().method(), path: url.pathname, status: response.status(), body })
})

async function screenshot(name) {
  await page.screenshot({ path: path.join(evidencePath, `${name}.png`), fullPage: true })
}
async function fillCommon({ kind = 'fx_settlement', currency = 'USD', bankNet, feeMode = 'none', feeAmount = '0', reference, rate = '7.100000', account = 'SYNTH-FX-02' }) {
  await page.getByLabel('事件类型').selectOption(kind)
  if (currency !== 'CNY') await page.getByLabel('来源币种').selectOption(currency)
  await page.getByLabel('银行净额（CNY）').fill(bankNet)
  await page.getByLabel('参考折算汇率').fill(rate)
  await page.getByLabel('手续费方式').selectOption(feeMode)
  if (feeMode === 'included') await page.getByLabel('含扣手续费（CNY）').fill(feeAmount)
  await page.getByLabel('来源银行账户标识').fill(account)
  await page.getByLabel('人民币账户标识').fill('SYNTH-CNY-02')
  await page.getByLabel('银行参考号').fill(reference)
  await page.getByLabel('凭证引用').fill('synthetic-bank-voucher.json')
  await page.getByLabel('凭证 SHA256').fill('89a84663e486a3a14a6ece97bc2ac9038703e60aeaa4189f302f6264a79519fc')
  await page.getByLabel('人工核实说明').fill('隔离合成凭证，已核对银行日期、净额、手续费与来源分配')
}
async function chooseSource(transactionNo, amount) {
  const search = page.locator('.source-toolbar input')
  await search.fill(transactionNo)
  const option = page.locator('.source-option').filter({ hasText: transactionNo })
  await option.getByRole('button', { name: '选择', exact: true }).click()
  const row = page.locator('.allocation-table tbody tr').filter({ hasText: transactionNo })
  await row.locator('input[type="number"]').fill(amount)
  await row.locator('.verification-toggle input').check()
}
async function createAndConfirm({ name, kind = 'fx_settlement', currency = 'USD', bankNet, feeMode = 'none', feeAmount = '0', reference, rate = '7.100000', sources, account = 'SYNTH-FX-02', abandon = false }) {
  console.log('REAL_UI_START', name)
  await page.getByRole('button', { name: '新建资金事件' }).click()
  await fillCommon({ kind, currency, bankNet, feeMode, feeAmount, reference, rate, account })
  if (kind === 'bank_fee') {
    const parent = page.getByLabel('关联结汇事件').locator('option').filter({ hasText: 'P2C-BANK-B-60' })
    await page.getByLabel('关联结汇事件').selectOption(await parent.getAttribute('value'))
  }
  for (const [transactionNo, amount] of sources) await chooseSource(transactionNo, amount)
  await page.getByRole('button', { name: '后端预览' }).click()
  await page.locator('.preview-box').waitFor()
  await screenshot(`${name}-preview-1440`)
  await page.getByRole('button', { name: '登记待确认草稿' }).click()
  await page.getByRole('heading', { name: '资金事件待确认' }).waitFor()
  await screenshot(`${name}-pending-1440`)
  if (abandon) {
    await page.getByRole('button', { name: '放弃草稿' }).click()
    await page.getByLabel('放弃原因').fill('P2-C 隔离验收：人工取消草稿')
    await page.getByRole('button', { name: '确认放弃草稿' }).click()
    await page.getByText('待确认草稿已留痕放弃').waitFor()
    await screenshot(`${name}-cancelled-1440`)
  } else {
    await page.getByRole('checkbox', { name: /我已核对以上银行凭证/ }).check()
    await page.getByRole('button', { name: '确认银行凭证' }).click()
    await page.getByText('资金事件已确认').waitFor()
    await screenshot(`${name}-confirmed-1440`)
  }
  const eventNo = await page.getByLabel('事件编号').inputValue().catch(() => null)
  const requestKey = await page.getByLabel('稳定请求键').inputValue().catch(() => null)
  await page.getByRole('button', { name: '关闭' }).last().click()
  console.log('REAL_UI_DONE', name)
  return { name, eventNo, requestKey, status: abandon ? 'cancelled' : 'confirmed' }
}

await page.goto(base, { waitUntil: 'networkidle' })
await page.getByRole('heading', { name: '银行资金记录' }).waitFor()
await screenshot('list-initial-1440')

const results = []
results.push(await createAndConfirm({ name: 'a-usd-60-included-fee', bankNet: '423.00', feeMode: 'included', feeAmount: '3.00', reference: 'P2C-BANK-A-60', sources: [['P2C-USD-A-60', '60']] }))
results.push(await createAndConfirm({ name: 'b-single-source-60', bankNet: '426.00', reference: 'P2C-BANK-B-60', sources: [['P2C-USD-B-100', '60']] }))
results.push(await createAndConfirm({ name: 'b-single-source-40', bankNet: '284.00', reference: 'P2C-BANK-B-40', sources: [['P2C-USD-B-100', '40']] }))
results.push(await createAndConfirm({ name: 'c-merge-30-70', bankNet: '700.00', reference: 'P2C-BANK-C-MERGE', rate: '7.000000', sources: [['P2C-USD-C-30', '30'], ['P2C-USD-C-70', '70']] }))
results.push(await createAndConfirm({ name: 'd-prepayment-source', bankNet: '355.00', reference: 'P2C-BANK-D-ADV', sources: [['P2C-USD-ADV', '50']] }))
results.push(await createAndConfirm({ name: 'f-independent-bank-fee', kind: 'bank_fee', currency: 'CNY', bankNet: '5.00', reference: 'P2C-BANK-FEE', rate: '1', account: 'SYNTH-CNY-02', sources: [['P2C-CNY-BANK-FEE', '5']] }))
results.push(await createAndConfirm({ name: 'g-cny-direct', kind: 'cny_direct', currency: 'CNY', bankNet: '20.00', reference: 'P2C-BANK-CNY', rate: '1', account: 'SYNTH-CNY-02', sources: [['P2C-CNY-DIRECT', '20']] }))
results.push(await createAndConfirm({ name: 'h-pending-abandon', bankNet: '87.60', reference: 'P2C-BANK-H', sources: [['P2C-USD-HIST-4DP', '12.34']], abandon: true }))

for (const [width, height] of [[1280, 800], [1024, 768]]) {
  await page.setViewportSize({ width, height })
  await page.reload({ waitUntil: 'networkidle' })
  await screenshot(`list-${width}`)
}
await fs.writeFile(path.join(evidencePath, 'real-ui-http.json'), JSON.stringify(observations, null, 2), 'utf8')
await fs.writeFile(path.join(evidencePath, 'real-ui-results.json'), JSON.stringify(results, null, 2), 'utf8')
await context.close()
await browser.close()
console.log(JSON.stringify({ REAL_UI_ACTION: results, REAL_API_OBSERVATION: observations.length }))
