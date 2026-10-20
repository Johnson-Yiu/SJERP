import { test, expect } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

const evidenceDir = path.resolve(process.cwd(), '..', 'docs', 'uat-evidence', 'r1-moq-02')

async function saveEvidence(page, name) {
  await page.screenshot({ path: path.join(evidenceDir, `${name}.png`), fullPage: true })
}

async function createPurchaseDraft(page, quantity, { tradeUnit = 'base', addSecondLine = false, expectWarning = false } = {}) {
  const purchaseRows = page.locator('.purchase-list-table tbody tr').filter({ hasText: '浏览器验收供应商' })
  const existingRowCount = await purchaseRows.count()
  await page.getByRole('button', { name: '新建采购单', exact: true }).click()
  const editor = page.getByRole('dialog', { name: '新建采购单', exact: true })
  await editor.getByRole('combobox', { name: '供应商', exact: true }).selectOption({ label: '浏览器验收供应商' })
  await editor.getByRole('checkbox').first().check()
  await expect(editor.getByText('MOQ 浏览器验收 SKU', { exact: true }).first()).toBeVisible()
  const sourceSelect = editor.getByRole('combobox', { name: '供应商供货档案', exact: true })
  await expect(sourceSelect).toBeVisible()
  const sourceOption = sourceSelect.locator('option').filter({ hasText: 'UAT-MOQ-MODEL' }).first()
  await expect(sourceOption).toHaveCount(1)
  const sourceValue = await sourceOption.getAttribute('value')
  expect(sourceValue).toBeTruthy()
  await sourceSelect.selectOption(sourceValue)
  const tradeUnitSelect = editor.getByRole('combobox', { name: '交易单位与包装规格' }).first()
  if (tradeUnit === 'base') {
    await tradeUnitSelect.selectOption('')
  } else {
    const tradeUnitOption = tradeUnitSelect.locator('option').filter({ hasText: '箱 · 10.00 pcs/box' }).first()
    await expect(tradeUnitOption).toHaveCount(1)
    await tradeUnitSelect.selectOption(await tradeUnitOption.getAttribute('value'))
  }
  const quantityInputs = editor.getByPlaceholder('采购数量')
  await quantityInputs.first().fill(String(quantity))
  if (addSecondLine) {
    await editor.getByRole('button', { name: '增加同 SKU 规格行' }).click()
    await expect(quantityInputs).toHaveCount(2)
    await quantityInputs.nth(1).fill(String(quantity))
  }
  if (expectWarning) {
    const warning = editor.getByTestId('draft-moq-warning')
    await expect(warning).toBeVisible()
    await expect(warning).toContainText('实际 60.00 pcs')
    await expect(warning).toContainText('MOQ 100.00 pcs')
    await expect(warning).toContainText('差额 40.00 pcs')
    await saveEvidence(page, '03-editor-moq-warning')
  }
  await editor.getByRole('button', { name: '创建采购单', exact: true }).click()
  await expect(editor).toHaveCount(0)
  await expect(purchaseRows).toHaveCount(existingRowCount + 1)
  const row = purchaseRows.first()
  await expect(row).toBeVisible()
  return row
}

test('R1-MOQ-02 real Chrome purchase flow keeps drafts, requires exception reason and records evidence', async ({ page }) => {
  test.skip(!process.env.R1_MOQ_02_REAL_UAT, 'Requires the isolated backend UAT service; run with R1_MOQ_02_REAL_UAT=1')
  test.setTimeout(60000)
  await mkdir(evidenceDir, { recursive: true })
  const responses = []
  page.on('response', response => {
    const url = new URL(response.url())
    if (url.pathname.startsWith('/api/purchase-orders')) responses.push({ method: response.request().method(), path: url.pathname, status: response.status() })
  })

  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/purchase-orders')
  await expect(page.getByRole('button', { name: '新建采购单', exact: true })).toBeVisible()
  const normalRow = await createPurchaseDraft(page, 100)
  await saveEvidence(page, '01-normal-draft-list')
  await normalRow.click()
  const normalDetail = page.getByRole('dialog', { name: '采购工作台', exact: true })
  await normalDetail.getByRole('button', { name: '确认下单', exact: true }).click()
  await page.getByTestId('dialog-confirm').click()
  await expect(page.getByText('采购单已确认下单。', { exact: true })).toBeVisible()
  await expect(normalDetail.locator('.status')).toHaveText('已下单')
  await saveEvidence(page, '02-normal-placed')
  await normalDetail.getByRole('button', { name: '关闭采购详情', exact: true }).click()

  const lowRow = await createPurchaseDraft(page, 3, { tradeUnit: 'box', addSecondLine: true, expectWarning: true })
  await lowRow.click()
  const lowDetail = page.getByRole('dialog', { name: '采购工作台', exact: true })
  await lowDetail.getByRole('button', { name: '确认下单', exact: true }).click()
  await page.getByTestId('dialog-confirm').click()
  const moqDialog = page.getByRole('dialog', { name: '采购 MOQ 例外确认', exact: true })
  await expect(moqDialog).toContainText('实际 60.00 pcs')
  await expect(moqDialog).toContainText('MOQ 100.00 pcs')
  await expect(moqDialog).toContainText('差额 40.00 pcs')
  await saveEvidence(page, '04-low-moq-confirmation')
  await page.getByTestId('dialog-cancel').click()
  await expect(moqDialog).toHaveCount(0)
  await expect(lowDetail.locator('.status')).toHaveText('草稿')
  await saveEvidence(page, '05-cancel-keeps-draft')

  await lowDetail.getByRole('button', { name: '确认下单', exact: true }).click()
  await page.getByTestId('dialog-confirm').click()
  await expect(page.getByRole('dialog', { name: '采购 MOQ 例外确认', exact: true })).toBeVisible()
  await page.getByTestId('dialog-input').fill('客户指定小批量试单，已确认本次需求量。')
  await page.getByRole('button', { name: '填写原因并继续下单', exact: true }).click()
  await expect(lowDetail.locator('.status')).toHaveText('已下单')
  await expect(page.getByTestId('purchase-moq-exception')).toContainText('客户指定小批量试单')
  await saveEvidence(page, '06-moq-exception-record')

  await lowDetail.getByRole('button', { name: '关闭采购详情', exact: true }).click()
  const reopenedRow = page.locator('.purchase-list-table tbody tr').filter({ hasText: '浏览器验收供应商' }).first()
  await expect(reopenedRow).toBeVisible()
  await reopenedRow.click()
  await expect(page.getByTestId('purchase-moq-exception')).toContainText('MOQ 例外确认')
  await saveEvidence(page, '07-reopen-exception')

  await page.setViewportSize({ width: 700, height: 900 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await saveEvidence(page, '08-narrow-workbench')
  await writeFile(path.join(evidenceDir, 'browser-log.json'), JSON.stringify({ browser: 'Chrome', viewport: { width: 700, height: 900 }, responses }, null, 2), 'utf8')
})
