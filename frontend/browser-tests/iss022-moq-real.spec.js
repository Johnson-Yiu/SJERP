import { test, expect } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const evidenceDir = process.env.ISS022_EVIDENCE_DIR
  ? path.resolve(process.env.ISS022_EVIDENCE_DIR)
  : path.resolve('../docs/uat-evidence/iss-022-procurement-moq')

async function selectOptionContaining(select, text) {
  const option = select.locator('option').filter({ hasText: text }).first()
  await expect(option).toHaveCount(1)
  await select.selectOption(await option.getAttribute('value'))
}

function writeEvidence(name, value) {
  fs.mkdirSync(evidenceDir, { recursive: true })
  fs.writeFileSync(path.join(evidenceDir, name), `${JSON.stringify(value, null, 2)}\n`, 'utf8')
}

async function openCreate(page) {
  await page.getByRole('button', { name: /新建采购单/ }).click()
  const editor = page.getByRole('dialog', { name: '新建采购单' })
  await expect(editor).toBeVisible()
  await editor.getByRole('combobox', { name: '供应商', exact: true }).selectOption({ label: 'ISS022 浏览器供应商' })
  const source = editor.locator('.sku-picker-options label').filter({ hasText: 'ISS022 浏览器测试 SKU' }).locator('input[type="checkbox"]')
  await source.check()
  await expect(editor.getByRole('combobox', { name: '供应商供货档案', exact: true })).toBeVisible()
  const supplierSource = editor.getByRole('combobox', { name: '供应商供货档案', exact: true })
  await expect(supplierSource.locator('option', { hasText: 'ISS022-BROWSER-SOURCE' })).toHaveCount(1)
  await selectOptionContaining(supplierSource, 'ISS022-BROWSER-SOURCE')
  return editor
}

async function saveDraft(editor) {
  await editor.getByRole('button', { name: /创建采购单|保存采购草稿/ }).click()
  await expect(editor).toBeHidden()
  await expect(editor.page().getByText(/采购草稿 .* 已保存|采购草稿已更新/)).toBeVisible()
}

async function firstRow(page) {
  const row = page.locator('.purchase-list-row').first()
  await expect(row).toBeVisible()
  return row
}

test.describe('ISS-022 采购 MOQ 真实浏览器回归', () => {
  test('等于 MOQ、低于 MOQ、交易单位换算、取消保留草稿及例外留痕', async ({ page }) => {
    test.setTimeout(120000)
    const responses = []
    page.on('response', async response => {
      if (!response.url().includes('/api/purchase-orders')) return
      if (!['GET', 'POST', 'PUT'].includes(response.request().method())) return
      responses.push({ method: response.request().method(), url: response.url(), status: response.status() })
    })

    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto('/purchase-orders')
    await expect(page.getByRole('button', { name: /新建采购单/ })).toBeVisible()

    const equalEditor = await openCreate(page)
    await equalEditor.getByPlaceholder('采购数量').fill('10')
    await page.screenshot({ path: path.join(evidenceDir, '01-equal-moq-draft.png'), fullPage: true })
    await saveDraft(equalEditor)
    const equalRow = await firstRow(page)
    await expect(equalRow).toContainText('草稿')
    await equalRow.getByRole('button', { name: /查看采购单/ }).click()
    const equalDetail = page.getByRole('dialog', { name: '采购工作台' })
    await expect(equalDetail).toBeVisible()
    await expect(equalDetail).toContainText('草稿')
    await page.screenshot({ path: path.join(evidenceDir, '02-equal-moq-detail.png'), fullPage: true })
    await equalDetail.getByRole('button', { name: '确认下单' }).click()
    await page.getByTestId('dialog-confirm').click()
    await expect(page.getByText('采购单已确认下单。')).toBeVisible()
    await expect(page.locator('.purchase-list-row').first()).toContainText('已下单')
    await page.screenshot({ path: path.join(evidenceDir, '03-equal-moq-ordered.png'), fullPage: true })
    await equalDetail.getByRole('button', { name: '关闭采购详情' }).click()

    const lowEditor = await openCreate(page)
    await selectOptionContaining(lowEditor.getByRole('combobox', { name: '交易单位与包装规格' }), '10 件箱')
    await lowEditor.getByPlaceholder('采购数量').fill('0.9')
    await expect(lowEditor.getByTestId('draft-moq-warning')).toContainText('实际 9.00 pcs')
    await expect(lowEditor.getByTestId('draft-moq-warning')).toContainText('MOQ 10.00 pcs')
    await page.screenshot({ path: path.join(evidenceDir, '04-low-moq-conversion-warning.png'), fullPage: true })
    await saveDraft(lowEditor)
    const lowRow = await firstRow(page)
    await lowRow.getByRole('button', { name: /查看采购单/ }).click()
    const lowDetail = page.getByRole('dialog', { name: '采购工作台' })
    await lowDetail.getByRole('button', { name: '确认下单' }).click()
    await page.getByTestId('dialog-confirm').click()
    const exceptionDialog = page.getByRole('dialog', { name: '采购 MOQ 例外确认' })
    await expect(exceptionDialog).toBeVisible()
    await expect(exceptionDialog).toContainText('实际 9.00 pcs')
    await page.screenshot({ path: path.join(evidenceDir, '05-low-moq-exception-dialog.png'), fullPage: true })
    await page.getByTestId('dialog-cancel').click()
    await expect(page.locator('.purchase-list-row').first()).toContainText('草稿')
    await page.screenshot({ path: path.join(evidenceDir, '06-cancel-keeps-draft.png'), fullPage: true })
    await lowDetail.getByRole('button', { name: '关闭采购详情' }).click()

    await page.locator('.purchase-list-row').first().getByRole('button', { name: /查看采购单/ }).click()
    await page.getByRole('dialog', { name: '采购工作台' }).getByRole('button', { name: '确认下单' }).click()
    await page.getByTestId('dialog-confirm').click()
    await expect(page.getByRole('dialog', { name: '采购 MOQ 例外确认' })).toBeVisible()
    await page.getByTestId('dialog-input').fill('客户指定小批量试单，已确认本次需求量。')
    await page.getByTestId('dialog-confirm').click()
    await expect(page.getByText('采购单已确认下单。')).toBeVisible()
    await expect(page.locator('.purchase-list-row').first()).toContainText('已下单')
    await lowDetail.getByRole('button', { name: '关闭采购详情' }).click()
    await page.locator('.purchase-list-row').first().getByRole('button', { name: /查看采购单/ }).click()
    const exceptionDetail = page.getByRole('dialog', { name: '采购工作台' })
    await expect(exceptionDetail.getByTestId('purchase-moq-exception')).toContainText('客户指定小批量试单')
    await expect(exceptionDetail.getByTestId('purchase-moq-exception')).toContainText('差额 1.00 pcs')
    await page.screenshot({ path: path.join(evidenceDir, '07-moq-exception-persisted.png'), fullPage: true })

    await exceptionDetail.getByRole('button', { name: '关闭采购详情' }).click()
    await page.getByRole('combobox', { name: '按状态筛选' }).selectOption('ordered')
    await expect(page.locator('.purchase-list-row')).toHaveCount(2)
    await page.screenshot({ path: path.join(evidenceDir, '08-ordered-filter.png'), fullPage: true })

    await page.setViewportSize({ width: 700, height: 900 })
    await page.goto('/purchase-orders?status=ordered')
    await expect(page.getByRole('button', { name: /新建采购单/ })).toBeVisible()
    const noHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)
    expect(noHorizontalOverflow).toBeTruthy()
    await page.screenshot({ path: path.join(evidenceDir, '09-narrow-purchase-list.png'), fullPage: true })
    writeEvidence('browser-log.json', { noHorizontalOverflow, responses })
  })
})
