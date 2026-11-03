import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test.use({ channel: 'chrome' })
const evidence = path.resolve(process.env.ISS039_EVIDENCE_ROOT || (process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT ? path.join(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'browser', 'iss039-amount-allocation') : '../docs/uat-evidence/r1-iss039-amount-allocation-fix-20261103/browser'))
const inspector = path.resolve('../docs/uat-evidence/r1-iss039-amount-allocation-fix-20261103/fixture.py')
fs.mkdirSync(evidence, { recursive: true })

function database(action) {
  if (!process.env.ISOLATED_TEST_PYTHON || !process.env.ISOLATED_TEST_RUN_ID) throw new Error('Use the verified isolated browser runner.')
  const result = spawnSync(process.env.ISOLATED_TEST_PYTHON, [inspector, action], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' })
  expect(result.status, result.stderr).toBe(0)
  return JSON.parse(result.stdout)
}

const fixtures = new Map()
test.beforeAll(() => {
  for (const width of [1440, 390]) fixtures.set(width, database('seed'))
})

for (const width of [1440, 390]) {
  test(`amount-only and deliberate legacy conversion, real Chrome ${width}px`, async ({ page }) => {
    test.setTimeout(120000)
    const http = []
    page.on('response', async response => {
      const request = response.request()
      if (response.url().includes('/cost-allocation')) {
        let body
        try { body = await response.json() } catch { body = null }
        http.push({ method: request.method(), path: new URL(response.url()).pathname, status: response.status(), request: request.postDataJSON(), body })
      }
    })
    const fixture = fixtures.get(width)
    const saveEvidence = (name, data) => fs.writeFileSync(path.join(evidence, `${width}-${name}.json`), JSON.stringify(data, null, 2))
    saveEvidence('fixture', fixture)
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 })
    async function api(method, purchase, suffix = '', data, status = 200) {
      const url = `/api/purchase-orders/${purchase.id}/cost-allocation${suffix}/`
      const response = await page.request[method](url, data === undefined ? {} : { data })
      const body = await response.json()
      http.push({ method: method.toUpperCase(), path: url, status: response.status(), request: data, body })
      expect(response.status(), JSON.stringify(body)).toBe(status)
      return body
    }
    async function open(purchase) {
      await page.goto('/purchase-orders')
      const row = page.locator('.purchase-list-row').filter({ hasText: purchase.no })
      await row.getByRole('button', { name: /查看采购单/ }).click()
      const detail = page.getByRole('dialog', { name: '采购工作台' })
      await detail.getByRole('button', { name: '分配采购成本 / 公共费用' }).click()
      const modal = page.getByRole('dialog', { name: /采购成本分配/ })
      await expect(modal.getByRole('button', { name: '保存成本分配', exact: true })).toBeVisible()
      return modal
    }
    const legacy = fixture.purchases.legacy
    const before = database('snapshot')
    let modal = await open(legacy)
    await expect(modal).toContainText('按数量比例（历史记录）')
    await expect(modal.locator('.cost-result')).toContainText('500.00')
    await expect(modal.getByRole('button', { name: '保存成本分配', exact: true })).toBeDisabled()
    await page.screenshot({ path: path.join(evidence, `${width}-01-legacy-readonly.png`) })
    await modal.getByRole('button', { name: '改按金额分摊并预览' }).click()
    await page.getByTestId('dialog-cancel').click()
    expect(database('snapshot')).toEqual(before)
    await expect(modal).toContainText('按数量比例（历史记录）')
    await modal.getByRole('button', { name: '改按金额分摊并预览' }).click()
    await page.getByTestId('dialog-confirm').click()
    await expect(modal.locator('.cost-result')).toContainText('909.09')
    await expect(modal.locator('.cost-result')).toContainText('90.91')
    expect(database('snapshot')).toEqual(before)
    await page.screenshot({ path: path.join(evidence, `${width}-02-amount-preview.png`) })
    await modal.locator('.cost-result').scrollIntoViewIfNeeded()
    await page.screenshot({ path: path.join(evidence, `${width}-05-amount-result.png`) })
    await modal.getByRole('button', { name: '取消', exact: true }).click()
    await page.getByTestId('dialog-confirm').click()
    expect(database('snapshot')).toEqual(before)
    modal = await open(legacy)
    await expect(modal).toContainText('按数量比例（历史记录）')
    await modal.getByRole('button', { name: '改按金额分摊并预览' }).click()
    await page.getByTestId('dialog-confirm').click()
    await expect(modal.locator('.cost-result')).toContainText('909.09')
    const saved = page.waitForResponse(r => r.url().endsWith(`/purchase-orders/${legacy.id}/cost-allocation/`) && r.request().method() === 'POST')
    await modal.getByRole('button', { name: '保存成本分配', exact: true }).click()
    expect((await saved).status()).toBe(200)
    await expect(modal).not.toContainText('历史记录按数量分摊')
    await page.screenshot({ path: path.join(evidence, `${width}-03-amount-saved.png`) })
    await page.reload()
    modal = await open(legacy)
    await expect(modal.locator('.cost-result')).toContainText('909.09')
    await expect(modal).not.toContainText('按数量比例（历史记录）')
    const summary = await api('get', legacy)
    const payload = { version: summary.version, allocations: summary.allocations.map(a => ({ purchase_item: a.purchase_item, target_type: a.target_type, order: a.order, quantity: a.quantity })), expenses: [{ name: '非法数量法', amount: '1000', method: 'quantity' }] }
    const committed = database('snapshot')
    await api('post', legacy, '', payload, 400)
    await api('post', legacy, '-preview', payload, 400)
    expect(database('snapshot')).toEqual(committed)
    const zero = fixture.purchases.zero
    await api('post', zero, '', { version: 0, allocations: [], expenses: [{ name: '正费用', amount: '1000', method: 'amount' }] }, 400)
    expect(database('snapshot')).toEqual(committed)
    await api('post', zero, '', { version: 0, allocations: [], expenses: [] })
    const fresh = fixture.purchases.new
    modal = await open(fresh)
    for (const [index, order] of fixture.orders.entries()) {
      const item = modal.locator('.cost-item').nth(index)
      await item.locator('.cost-row select').first().selectOption('order')
      await item.locator('.cost-row select').nth(1).selectOption(String(order))
    }
    await modal.getByRole('button', { name: '添加附加费用' }).click()
    await modal.getByLabel('金额（CNY）', { exact: true }).fill('1000')
    await expect(modal.locator('.cost-result')).toContainText('909.09')
    await expect(modal.locator('option[value="quantity"]')).toHaveCount(0)
    const freshSaved = page.waitForResponse(r => r.url().endsWith(`/purchase-orders/${fresh.id}/cost-allocation/`) && r.request().method() === 'POST')
    await modal.getByRole('button', { name: '保存成本分配', exact: true }).click()
    expect((await freshSaved).status()).toBe(200)
    await expect(modal.locator('.pending-badge')).toHaveCount(0)
    await modal.locator('.cost-result').scrollIntoViewIfNeeded()
    await page.screenshot({ path: path.join(evidence, `${width}-04-new-amount.png`) })
    const final = database('snapshot')
    const allowed = new Set(['crm.PurchaseOrder', 'crm.PurchaseCostAllocation', 'crm.OperationLog', 'crm.InventoryReservation'])
    expect(Object.fromEntries(Object.entries(final).filter(([key]) => !allowed.has(key)))).toEqual(Object.fromEntries(Object.entries(before).filter(([key]) => !allowed.has(key))))
    const savedNew = await api('get', fresh)
    expect(savedNew.allocations.map(row => Number(row.additional_amount))).toEqual([909.09, 90.91])
    expect(savedNew.allocations.map(row => row.order)).toEqual(fixture.orders)
    saveEvidence('database-final', final)
    saveEvidence('http', http)
  })
}
