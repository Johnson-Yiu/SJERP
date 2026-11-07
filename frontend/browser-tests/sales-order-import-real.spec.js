import { createHash } from 'node:crypto'
import { readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'

import { expect, test } from '@playwright/test'

const evidenceDir = process.env.SALES_ORDER_IMPORT_EVIDENCE_DIR
if (!evidenceDir) throw new Error('SALES_ORDER_IMPORT_EVIDENCE_DIR must be set by the isolated test runner.')

test.use({ acceptDownloads: true, viewport: { width: 1600, height: 1000 } })

test('authenticated codex superuser imports XLSX and downloads the actual error CSV', async ({ page }) => {
  const identityResponse = await page.request.get('/api/session/current-operator/')
  expect(identityResponse.status()).toBe(200)
  const identity = await identityResponse.json()
  expect(identity).toMatchObject({
    name: 'codex',
    role: '超级管理员',
    authenticated: true,
    development_superadmin: false,
    rbac_enforcement: false,
    has_all_permissions: true,
  })

  const fixture = JSON.parse(await readFile(path.join(evidenceDir, 'fixture.json'), 'utf8'))
  const workbookPath = path.join(evidenceDir, fixture.workbook)
  await page.goto('/import')
  await page.getByRole('tab', { name: '销售订单', exact: true }).click()

  const templateDownloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: /下载销售订单 XLSX 模板/ }).click()
  const templateDownload = await templateDownloadPromise
  expect(templateDownload.suggestedFilename()).toBe('sales-order-import-template.xlsx')
  const templatePath = path.join(evidenceDir, templateDownload.suggestedFilename())
  await templateDownload.saveAs(templatePath)
  const templateBytes = await readFile(templatePath)
  expect(templateBytes.subarray(0, 2).toString('hex')).toBe('504b')

  await page.locator('input[type="file"][accept*=".xlsx"]').setInputFiles(workbookPath)
  await page.getByRole('button', { name: '预览并校验', exact: true }).click()
  await page.getByText('共 3 条明细、2 张订单：1 张可导入，1 张待修正', { exact: true }).waitFor()
  await page.getByText(`找不到 SKU：${fixture.invalid_sku}。`, { exact: true }).waitFor()

  const executeResponsePromise = page.waitForResponse(response =>
    new URL(response.url()).pathname === '/api/import/orders/execute/' && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: '确认导入 1 张草稿', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toContainText('导入不会确认订单、占库存、生成应收计划或登记发货。')
  await page.getByTestId('dialog-confirm').click()
  const executeResponse = await executeResponsePromise
  expect(executeResponse.status()).toBe(200)
  const result = await executeResponse.json()
  expect(result).toMatchObject({ created_orders: 1, failed_orders: 1, total_orders: 2 })
  expect(result.orders).toHaveLength(1)
  expect(result.orders[0]).toMatchObject({ source_order_no: fixture.valid_source_order, status: 'draft', line_count: 2 })
  await page.getByText('已创建 1 张草稿，1 张未创建', { exact: true }).waitFor()

  const errorDownloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载错误清单 CSV', exact: true }).click()
  const errorDownload = await errorDownloadPromise
  expect(errorDownload.suggestedFilename()).toBe('sales-order-import-errors.csv')
  const csvPath = path.join(evidenceDir, errorDownload.suggestedFilename())
  await errorDownload.saveAs(csvPath)
  const csvBytes = await readFile(csvPath)
  const csvText = csvBytes.toString('utf8')
  expect(csvText.startsWith('\ufeff')).toBe(true)
  expect(csvText).toContain(fixture.invalid_source_order)
  expect(csvText).toContain(fixture.invalid_sku)
  expect(csvText).toContain('找不到 SKU')

  const resultLookup = await page.request.get(`/api/import/orders/results/${result.batch_id}/`)
  expect(resultLookup.status()).toBe(200)
  expect(await resultLookup.json()).toEqual(result)

  const desktopScreenshot = path.join(evidenceDir, 'sales-order-import-1600.png')
  await page.screenshot({ path: desktopScreenshot, fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect.poll(() => page.locator('.sidebar').evaluate(element => element.getBoundingClientRect().right)).toBeLessThanOrEqual(1)
  const mobileScreenshot = path.join(evidenceDir, 'sales-order-import-390.png')
  await page.screenshot({ path: mobileScreenshot, fullPage: true })
  const dimensions = await page.evaluate(() => ({
    viewportWidth: document.documentElement.clientWidth,
    documentWidth: document.documentElement.scrollWidth,
  }))
  expect(dimensions.documentWidth).toBeLessThanOrEqual(dimensions.viewportWidth)

  await writeFile(path.join(evidenceDir, 'browser-results.json'), JSON.stringify({
    identity: {
      username: identity.name,
      role: identity.role,
      authenticated: identity.authenticated,
      development_superadmin: identity.development_superadmin,
      rbac_enforcement: identity.rbac_enforcement,
    },
    template: { filename: templateDownload.suggestedFilename(), bytes: templateBytes.length },
    import: {
      rows: result.total_rows,
      orders: result.total_orders,
      created: result.created_orders,
      failed: result.failed_orders,
      order_no: result.orders[0].order_no,
      status: result.orders[0].status,
    },
    csv: {
      filename: errorDownload.suggestedFilename(),
      bytes: csvBytes.length,
      sha256: createHash('sha256').update(csvBytes).digest('hex'),
      hasUtf8Bom: csvBytes.subarray(0, 3).equals(Buffer.from([0xef, 0xbb, 0xbf])),
      includesInvalidSourceAndSku: csvText.includes(fixture.invalid_source_order) && csvText.includes(fixture.invalid_sku),
    },
    desktopScreenshot: path.basename(desktopScreenshot),
    mobileScreenshot: path.basename(mobileScreenshot),
    mobileDimensions: dimensions,
  }, null, 2), 'utf8')
})
