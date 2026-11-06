import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const require = createRequire(path.join(process.cwd(), 'package.json'))
const { chromium } = require('playwright')

const evidenceDir = path.dirname(fileURLToPath(import.meta.url))
const baseUrl = process.env.CRM_BASE_URL || 'http://127.0.0.1:5277'
const workbookPath = process.env.CRM_SALES_ORDER_IMPORT_XLSX
if (!workbookPath) throw new Error('Set CRM_SALES_ORDER_IMPORT_XLSX to the synthetic workbook created by seed-chrome-visual.py.')

const browser = await chromium.launch({ channel: 'chrome', headless: false })
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, acceptDownloads: true })
const pageErrors = []
page.on('pageerror', error => pageErrors.push(error.message))

try {
  await page.goto(`${baseUrl}/import`, { waitUntil: 'domcontentloaded' })
  await page.getByRole('tab', { name: '销售订单' }).click()

  const templateDownloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: /下载销售订单 XLSX 模板/ }).click()
  const templateDownload = await templateDownloadPromise
  assert.equal(templateDownload.suggestedFilename(), 'sales-order-import-template.xlsx')

  await page.locator('input[type="file"][accept*=".xlsx"]').setInputFiles(workbookPath)
  await page.getByRole('button', { name: '预览并校验', exact: true }).click()
  await page.getByText('共 3 条明细、2 张订单：1 张可导入，1 张待修正', { exact: true }).waitFor()
  await page.getByText('预览不会写入业务数据，有明细错误时整单不导入。').waitFor()
  await page.getByRole('table').getByText('UAT-EXT-ORDER-001').waitFor()
  await page.getByRole('table').getByText('UAT-UNKNOWN-SKU').waitFor()

  const executionResponsePromise = page.waitForResponse(response => response.url().includes('/api/import/orders/execute/') && response.request().method() === 'POST')
  await page.getByRole('button', { name: '确认导入 1 张草稿' }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByText('导入不会确认订单、占库存、生成应收计划或登记发货。').waitFor()
  await page.getByTestId('dialog-confirm').click()
  const executionResponse = await executionResponsePromise
  assert.equal(executionResponse.status(), 200)
  const execution = await executionResponse.json()
  assert.equal(execution.created_orders, 1)
  assert.equal(execution.failed_orders, 1)
  await page.getByText('已创建 1 张草稿，1 张未创建', { exact: true }).waitFor()
  await page.getByRole('table').getByText('UAT-EXT-ORDER-001').waitFor()
  await page.getByRole('table').getByText('草稿', { exact: true }).waitFor()
  await page.getByRole('table').getByText('找不到 SKU：UAT-UNKNOWN-SKU。').waitFor()
  await page.screenshot({ path: path.join(evidenceDir, 'chrome-sales-order-import.png'), fullPage: true })

  const errorDownloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载错误清单 CSV' }).click()
  const errorDownload = await errorDownloadPromise
  assert.equal(errorDownload.suggestedFilename(), 'sales-order-import-errors.csv')
  const errorFile = await errorDownload.path()
  const errorCsv = await readFile(errorFile, 'utf8')
  assert.match(errorCsv, /UAT-UNKNOWN-SKU/)

  assert.deepEqual(pageErrors, [])
  console.log(JSON.stringify({
    browser: 'Google Chrome (system channel)',
    url: `${baseUrl}/import`,
    template: templateDownload.suggestedFilename(),
    preview: { rows: execution.total_rows, orders: execution.total_orders, created: execution.created_orders, failed: execution.failed_orders },
    result: { createdOrder: execution.orders[0]?.order_no, status: execution.orders[0]?.status, downloadedErrors: errorDownload.suggestedFilename() },
    screenshot: path.join(evidenceDir, 'chrome-sales-order-import.png'),
    pageErrors,
  }, null, 2))
} finally {
  await browser.close()
}
