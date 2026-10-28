import { test, expect } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const evidenceDir = process.env.ISS075_EVIDENCE_DIR
  ? path.resolve(process.env.ISS075_EVIDENCE_DIR)
  : path.resolve('../docs/uat-evidence/iss-075-payment-terms')

function screenshotPath(name) {
  fs.mkdirSync(evidenceDir, { recursive: true })
  return path.join(evidenceDir, name)
}

async function selectSupplierAndSku(editor) {
  await editor.getByRole('combobox', { name: '供应商', exact: true }).selectOption({ label: 'ISS075 浏览器供应商' })
  const sku = editor.locator('.sku-picker-options label').filter({ hasText: 'ISS075 浏览器测试 SKU' }).locator('input[type="checkbox"]')
  await sku.check()
  await expect(editor.getByRole('combobox', { name: '供应商供货档案', exact: true })).toBeVisible()
}

test.describe('ISS-075 供应商固定付款规则退出常规前端真实浏览器回归', () => {
  test('供应商 UI、空付款条件草稿/正式 PO、历史付款计划与窄屏', async ({ page }) => {
    test.setTimeout(120000)
    const apiLog = []
    page.on('response', response => {
      if (response.url().includes('/api/') && ['GET', 'POST', 'PUT', 'PATCH'].includes(response.request().method())) {
        apiLog.push({ method: response.request().method(), url: response.url(), status: response.status() })
      }
    })
    // Keep external font delivery from blocking this local visual regression; fallback fonts are part of the UI.
    await page.route('https://fonts.googleapis.com/**', route => route.abort())
    await page.route('https://fonts.gstatic.com/**', route => route.abort())

    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto('/suppliers')
    await expect(page.getByRole('button', { name: /新建供应商/ })).toBeVisible()
    await expect(page.getByText('系统执行付款规则')).toHaveCount(0)
    await expect(page.getByLabel('按付款规则筛选')).toHaveCount(0)
    await page.screenshot({ path: screenshotPath('01-supplier-list-no-fixed-rule.png'), fullPage: true })

    await page.getByRole('button', { name: /新建供应商/ }).click()
    const supplierEditor = page.getByRole('dialog', { name: '新建供应商' })
    await expect(supplierEditor).toBeVisible()
    await expect(supplierEditor.getByText('系统执行付款规则')).toHaveCount(0)
    await supplierEditor.getByRole('button', { name: '取消' }).click()

    await page.goto('/purchase-orders')
    await page.getByRole('button', { name: /新建采购单/ }).click()
    const draftEditor = page.getByRole('dialog', { name: '新建采购单' })
    await selectSupplierAndSku(draftEditor)
    await expect(draftEditor.locator('[aria-label^="阶段名称"]')).toHaveCount(0)
    await expect(draftEditor.getByText('未协商时可暂不填写')).toBeVisible()
    await expect(draftEditor.getByRole('button', { name: '使用系统默认' })).toHaveCount(0)
    await draftEditor.getByPlaceholder('采购数量').fill('1')
    await draftEditor.getByPlaceholder(/采购单价/).fill('100')
    await page.screenshot({ path: screenshotPath('02-new-po-empty-payment-terms.png'), fullPage: true })
    await draftEditor.getByRole('button', { name: '保存采购草稿' }).click()
    await expect(draftEditor).toBeHidden()
    await expect(page.getByText(/采购草稿 .* 已保存/)).toBeVisible()

    const draftRow = page.locator('.purchase-list-row').filter({ hasText: '草稿' }).first()
    await expect(draftRow).toBeVisible()
    const draftNo = await draftRow.locator('td').first().innerText()
    await draftRow.getByRole('button', { name: /查看采购单/ }).click()
    const draftDetail = page.getByRole('dialog', { name: '采购工作台' })
    await draftDetail.getByRole('button', { name: '确认采购下单' }).click()
    await page.getByTestId('dialog-confirm').click()
    await expect(page.getByText('采购单已确认下单。')).toBeVisible()
    await expect(page.locator('.purchase-list-row').filter({ hasText: draftNo })).toContainText('已下单')
    await draftDetail.getByRole('button', { name: '供应商应付', exact: true }).click()
    await expect(draftDetail).toContainText('暂无应付计划。')
    await draftDetail.getByRole('button', { name: '关闭采购详情' }).click()

    const historyRow = page.locator('.purchase-list-row').filter({ hasText: 'ISS075-HISTORY-01' }).first()
    await expect(historyRow).toBeVisible()
    await historyRow.getByRole('button', { name: /查看采购单/ }).click()
    const historyDetail = page.getByRole('dialog', { name: '采购工作台' })
    await historyDetail.getByRole('button', { name: '供应商应付', exact: true }).click()
    await expect(historyDetail).toContainText('首付款')
    await expect(historyDetail).toContainText('尾款')
    await expect(historyDetail).toContainText('500.00')
    await page.screenshot({ path: screenshotPath('03-history-po-payment-plan.png'), fullPage: true })
    await historyDetail.getByRole('button', { name: '关闭采购详情' }).click()

    await page.setViewportSize({ width: 700, height: 900 })
    await page.goto('/suppliers')
    await expect(page.getByRole('button', { name: /新建供应商/ })).toBeVisible()
    await expect(page.getByText('ISS075 浏览器供应商')).toBeVisible()
    const noHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)
    expect(noHorizontalOverflow).toBeTruthy()
    await page.screenshot({ path: screenshotPath('04-narrow-supplier-list.png'), fullPage: true })
    fs.writeFileSync(screenshotPath('browser-log.json'), `${JSON.stringify({ noHorizontalOverflow, apiLog }, null, 2)}\n`, 'utf8')
  })
})
