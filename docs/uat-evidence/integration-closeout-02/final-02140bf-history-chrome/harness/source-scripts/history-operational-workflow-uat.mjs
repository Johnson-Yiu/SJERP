import { readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { chromium, expect } from '@playwright/test'

const origin = process.env.HISTORY_UAT_ORIGIN
const dir = process.env.HISTORY_UAT_SESSION_DIR
const evidence = process.env.HISTORY_UAT_EVIDENCE_DIR
if (!origin || !dir || !evidence) throw new Error('Isolated UAT environment is required')
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(origin) || !path.basename(dir).startsWith('sunjack-history-operational-closeout-')) throw new Error('Only a marked loopback synthetic UAT environment is allowed')
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const errors = []
async function session(file) {
  const { sessionid, csrftoken } = JSON.parse(await readFile(path.join(dir, file), 'utf8'))
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
  await context.addCookies([{ name: 'sessionid', value: sessionid, url: origin, httpOnly: true, sameSite: 'Lax' }, { name: 'csrftoken', value: csrftoken, url: origin, sameSite: 'Lax' }])
  const page = await context.newPage()
  page.on('pageerror', error => errors.push(error.message))
  page.on('dialog', dialog => dialog.accept())
  await page.goto(`${origin}/history-takeover`, { waitUntil: 'networkidle' })
  await expect(page.getByRole('heading', { name: '执行结果' })).toBeVisible()
  return page
}
async function open(page, summary, button) {
  const detail = page.locator('details').filter({ has: page.getByText(summary, { exact: true }) })
  if (!await detail.evaluate(el => el.open)) await detail.locator('summary').click()
  await detail.getByRole('button', { name: button }).click()
  await expect(detail.getByRole('button', { name: button })).toBeEnabled()
  return detail
}
async function choose(label, value) { await label.locator('select').selectOption(value) }
async function optionValue(label, text) { return await label.locator('option').filter({ hasText: text }).first().getAttribute('value') }
async function refreshFinance(page) { return open(page, '历史资金接续', '读取资金来源、账户和凭证') }

try {
  const maker = await session('session.json')
  const reviewer = await session('reviewer-session.json')
  for (const [source, date, amount] of [['TX-SO-1', '2024-09-03', '287.43'], ['TX-PO-1', '2024-09-04', '35.00']]) {
    let panel = await refreshFinance(maker)
    if ((await panel.locator('.takeover-remainder-item').filter({ hasText: source }).innerText()).includes('资金事实 #')) continue
    const sourceLabel = panel.getByLabel('历史收付款来源')
    await sourceLabel.selectOption(await optionValue(panel.locator('label').filter({ hasText: '历史收付款来源' }), source))
    await panel.getByLabel('自有人民币账户').selectOption({ label: '合成验收账户 (UAT-HISTORY-CNY)' })
    const voucherLabel = panel.locator('label').filter({ hasText: '实际凭证' })
    await choose(voucherLabel, await optionValue(voucherLabel, 'synthetic-uat.pdf'))
    await panel.getByLabel('实际发生日期').fill(date)
    await panel.getByLabel('实际人民币金额').fill(amount)
    await panel.getByLabel('核实依据').fill('合成凭证核验')
    await panel.getByRole('button', { name: '保存资金指令' }).click()
    await expect(panel.locator('.takeover-remainder-item').filter({ hasText: source }).getByRole('button', { name: '复核指令' })).toBeVisible()
    panel = await refreshFinance(reviewer)
    await panel.locator('.takeover-remainder-item').filter({ hasText: source }).getByRole('button', { name: '复核指令' }).click()
    await expect(panel.locator('.takeover-remainder-item').filter({ hasText: source }).getByRole('button', { name: '核对凭证并记账' })).toBeVisible()
    panel = await refreshFinance(maker)
    await panel.locator('.takeover-remainder-item').filter({ hasText: source }).getByRole('button', { name: '核对凭证并记账' }).click()
    await expect(panel.locator('.takeover-remainder-item').filter({ hasText: source })).toContainText('资金事实 #')
  }
  let panel = await open(maker, '库存盘点基准', '读取盘点来源')
  if (!await panel.getByRole('button', { name: '启用盘点基准' }).count() && !(await panel.innerText()).includes('基准记录 1 条')) {
  await panel.getByLabel('货物所有权').selectOption('own')
  await panel.getByLabel('核实单位成本').fill('3.25')
  await panel.getByLabel('成本币种').fill('USD')
  await panel.getByLabel('已核实这些 SKU 的盘点范围完整').check()
  await panel.getByLabel('盘点与成本依据').fill('合成盘点与成本凭证')
  await panel.getByRole('button', { name: '保存基准申请' }).click()
  panel = await open(reviewer, '库存盘点基准', '读取盘点来源')
  await panel.getByLabel('复核或撤销依据').fill('复核合成盘点')
  await panel.getByRole('button', { name: '复核基准' }).click()
  await expect(panel.getByRole('button', { name: '启用盘点基准' })).toBeVisible()
  panel = await open(maker, '库存盘点基准', '读取盘点来源')
  }
  if (await panel.getByRole('button', { name: '启用盘点基准' }).count()) await panel.getByRole('button', { name: '启用盘点基准' }).click()
  await expect(panel).toContainText('基准记录 1 条')
  panel = await open(maker, '未结余额与剩余业务', '读取合同与未结来源')
  await panel.getByLabel('启用日期').fill('2025-01-01')
  await panel.getByLabel('接续核实依据').fill('合成合同与余额核验')
  const sale = panel.locator('section.takeover-remainder').filter({ has: maker.locator('h4').filter({ hasText: '销售订单 ·' }) })
  const purchase = panel.locator('section.takeover-remainder').filter({ has: maker.locator('h4').filter({ hasText: '采购订单 ·' }) })
  for (const section of [sale, purchase]) {
    await section.getByLabel('未结承接方式').selectOption('itemized')
    await section.getByLabel('余额核实依据').fill('合成计划与流水')
  }
  await sale.getByLabel('核实单位成本').fill('3.25')
  await sale.getByLabel(/成本币种/).fill('USD')
  await sale.getByLabel('成本依据').fill('合成成本凭证')
  await sale.getByLabel('剩余运费').fill('0')
  await sale.getByLabel('剩余折扣').fill('0')
  await sale.getByLabel('金额依据').fill('合成合同')
  await purchase.getByLabel('手工来源依据').fill('合成供应商合同')
  await purchase.getByLabel('采购归属').selectOption('order')
  const salesSelect = purchase.locator('label').filter({ hasText: /^销售订单/ }).locator('select')
  await salesSelect.selectOption({ index: 1 })
  await purchase.getByLabel('已核实本次接续没有额外公共费用').check()
  await purchase.getByLabel('费用核实依据').fill('合成合同')
  await panel.getByRole('button', { name: '保存接续申请' }).click()
  await expect(panel.getByRole('button', { name: '复核接续申请' })).toBeVisible()
  panel = await open(reviewer, '未结余额与剩余业务', '读取合同与未结来源')
  await panel.getByLabel('复核依据').fill('合成合同、余额与成本复核')
  await panel.getByRole('button', { name: '复核接续申请' }).click()
  await expect(panel.getByRole('button', { name: '启用未结并建立草稿' })).toBeVisible()
  panel = await open(maker, '未结余额与剩余业务', '读取合同与未结来源')
  await panel.getByRole('button', { name: '启用未结并建立草稿' }).click()
  await expect(panel.getByRole('button', { name: '确认销售接续单' })).toBeVisible()
  await panel.getByRole('button', { name: '确认销售接续单' }).click()
  await expect(panel.getByRole('button', { name: '确认销售接续单' })).toHaveCount(0)
  await panel.getByRole('button', { name: '确认采购下单' }).click()
  await expect(panel.getByRole('button', { name: '确认采购下单' })).toHaveCount(0)
  await expect(maker.getByText('整体进度：适用项目已接续。')).toBeVisible()
  await maker.screenshot({ path: path.join(evidence, 'history-operational-workflow-1440.png'), fullPage: true })
  await maker.setViewportSize({ width: 390, height: 844 }); await maker.waitForTimeout(700)
  await maker.screenshot({ path: path.join(evidence, 'history-operational-workflow-390.png'), fullPage: true })
  if (errors.length) throw new Error(errors.join('; '))
  const result = { chrome: browser.version(), database: 'isolated synthetic SQLite', workflow: 'archive, two source cash facts with separate reviewer, inventory baseline, itemized balances and confirmed continuation drafts', screenshots: ['history-operational-workflow-1440.png', 'history-operational-workflow-390.png'], errors }
  await writeFile(path.join(evidence, 'chrome-workflow.json'), JSON.stringify(result, null, 2) + '\n')
  console.log(JSON.stringify(result, null, 2))
} finally { await browser.close() }
