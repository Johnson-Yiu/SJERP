import { test, expect } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'

test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== 'prelaunch-p1-05-feedback-02.spec.js', 'Requires its dedicated isolated codex profile and synthetic fixtures.')
test.use({ channel: 'chrome', viewport: { width: 1366, height: 768 } })
test('P1-05 packaging and procurement pending failure recovery and persisted success', async ({ page, browser }, info) => {
  test.setTimeout(240000)
  const output = info.outputPath('p1-05')
  await mkdir(output, { recursive: true })
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [path.resolve('../docs/uat-evidence/ui-sales-completion-02/seed.py')], { env: process.env, encoding: 'utf8' }))
  const results = []
  const capture = async state => {
    for (const [width, height] of [[1366, 768], [1920, 1080]]) {
      await page.setViewportSize({ width, height })
      await page.screenshot({ path: path.join(output, `${state}-${width}.png`) })
      expect(await page.evaluate(() => devicePixelRatio)).toBe(1)
    }
    await page.setViewportSize({ width: 1366, height: 768 })
  }
  await page.goto('/quotes?create=1&customer=' + fixture.customer)
  const editor = page.getByRole('form', { name: '报价编辑器' })
  await editor.locator('.sku-picker-options label').filter({ hasText: 'SYNTH-SALES-SKU-001' }).getByRole('checkbox').check()
  await editor.getByRole('button', { name: '生成预计装箱方案' }).click()
  await editor.getByRole('button', { name: /补充默认包装/ }).click()
  const packaging = page.locator('.packaging-config-modal')
  await packaging.locator('select').selectOption(String(fixture.carton))
  await packaging.getByRole('spinbutton').nth(0).fill('5')
  await packaging.getByRole('spinbutton').nth(1).fill('0.5')
  let releasePackaging
  const packagingHeld = new Promise(resolve => { releasePackaging = resolve })
  await page.route('**/api/skus/*/packaging/', async route => {
    if (route.request().method() !== 'PUT') return route.continue()
    await packagingHeld
    await route.fulfill({ status: 503, json: { detail: '合成包装保存失败，请重试。' } })
  })
  await packaging.getByRole('button', { name: '保存默认包装' }).click()
  await expect(packaging.getByRole('button', { name: '保存中...' })).toBeDisabled()
  await expect(packaging.getByRole('button', { name: '取消' })).toBeDisabled()
  await capture('packaging-pending')
  releasePackaging()
  await expect(packaging.getByRole('alert')).toContainText('默认包装保存失败')
  await expect(packaging.getByRole('spinbutton').first()).toHaveValue('5')
  await capture('packaging-failed')
  await page.unroute('**/api/skus/*/packaging/')
  const packaged = page.waitForResponse(r => r.url().endsWith('/packaging/') && r.request().method() === 'PUT')
  await packaging.getByRole('button', { name: '保存默认包装' }).click()
  const packagingResponse = await packaged
  expect(packagingResponse.status()).toBe(200)
  const packagingReadback = await page.request.get(packagingResponse.url())
  expect(packagingReadback.status()).toBe(200)
  const pack = await packagingReadback.json()
  expect(Number(pack.effective.effective_qty_per_carton)).toBe(5)
  await expect(packaging).toHaveCount(0)
  await capture('packaging-success')
  results.push({ key: 'packaging', save: 200, readback: pack })
  await editor.getByRole('button', { name: '取消', exact: true }).click()
  await page.getByRole('button', { name: '放弃修改', exact: true }).click()

  await page.goto('/orders?detail=' + fixture.procurementOrder)
  const workbench = page.getByRole('dialog', { name: '订单工作台' })
  await workbench.getByRole('button', { name: '采购与发货', exact: true }).click()
  await page.getByRole('button', { name: '生成采购草稿', exact: true }).click()
  const drawer = page.getByRole('dialog', { name: '采购草稿预览' })
  let releasePurchase
  const purchaseHeld = new Promise(resolve => { releasePurchase = resolve })
  await page.route('**/generate-purchase-drafts/', async route => {
    await purchaseHeld
    await route.fulfill({ status: 503, json: { detail: '合成采购草稿创建失败，请重试。' } })
  })
  await drawer.getByRole('button', { name: '创建 采购草稿' }).click()
  await expect(drawer.getByRole('button', { name: '创建中…' })).toBeDisabled()
  await capture('procurement-pending')
  // A pending write must not lose its result by closing the drawer.
  try {
    await expect(drawer.getByRole('button', { name: '关闭', exact: true })).toBeDisabled()
    await expect(drawer.getByRole('button', { name: '取消', exact: true })).toBeDisabled()
    await expect(drawer).toBeVisible()
  } finally { releasePurchase() }
  await expect(drawer.getByRole('alert')).toContainText('合成采购草稿创建失败')
  await capture('procurement-failed')
  await page.unroute('**/generate-purchase-drafts/')
  const created = page.waitForResponse(r => r.url().endsWith('/generate-purchase-drafts/') && r.request().method() === 'POST')
  await drawer.getByRole('button', { name: '创建 采购草稿' }).click()
  const response = await created
  expect(response.status()).toBe(201)
  const body = await response.json()
  expect(body.created_count).toBe(1)
  const draft = body.purchase_orders[0]
  const readback = await page.request.get(`/api/purchase-orders/${draft.id}/`)
  const record = await readback.json()
  expect(record.status).toBe('draft')
  expect(Number(record.items[0].quantity)).toBe(15)
  await expect(drawer).toHaveCount(0)
  await expect(workbench.getByRole('link', { name: draft.purchase_no })).toBeVisible()
  await capture('procurement-success')
  await page.reload()
  await workbench.getByRole('button', { name: '采购与发货', exact: true }).click()
  await expect(page.getByRole('button', { name: '生成采购草稿', exact: true })).toBeDisabled()
  results.push({ key: 'procurement', save: 201, id: draft.id, quantity: record.items[0].quantity, reopenedCannotDuplicate: true })
  await writeFile(path.join(output, 'result.json'), JSON.stringify({ source: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(), browser: browser.version(), results }, null, 2))
})

test('authenticated codex superuser imports XLSX and downloads the actual error CSV', async ({ page }) => {
  test.setTimeout(180000)
  const evidenceDir = path.join(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'browser', 'sales-order-import-real.spec')
  await mkdir(evidenceDir, { recursive: true })
  execFileSync(process.env.ISOLATED_TEST_PYTHON, [path.resolve('../backend/test_support/seed_sales_order_import_browser.py')], {
    cwd: path.resolve('../backend'), env: { ...process.env, SALES_ORDER_IMPORT_EVIDENCE_DIR: evidenceDir }, encoding: 'utf8',
  })
  const capture = async state => {
    for (const [width, height] of [[1366, 768], [1920, 1080]]) {
      await page.setViewportSize({ width, height })
      await page.screenshot({ path: path.join(evidenceDir, `${state}-${width}.png`) })
      expect(await page.evaluate(() => devicePixelRatio)).toBe(1)
    }
    await page.setViewportSize({ width: 1366, height: 768 })
  }
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

  let savedResult, resolveSaved, releaseResponse
  const saved = new Promise(resolve => { resolveSaved = resolve })
  const released = new Promise(resolve => { releaseResponse = resolve })
  await page.route('**/api/import/orders/execute/', async route => {
    const token = route.request().postData().match(/name="preview_token"\r\n\r\n([^\r\n]+)/)?.[1]
    expect(token).toBeTruthy()
    const response = await page.request.post(route.request().url(), { headers: { 'X-CSRFToken': route.request().headers()['x-csrftoken'] }, multipart: { file: { name:path.basename(workbookPath), mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer:await readFile(workbookPath) }, preview_token:token } })
    savedResult = await response.json(); await writeFile(path.join(evidenceDir, 'lost-response-result.json'), JSON.stringify({status:response.status(),body:savedResult},null,2)); resolveSaved()
    await released; await route.abort('failed')
  })
  await page.getByRole('button', { name: '确认导入 1 张草稿', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toContainText('导入不会确认订单、占库存、生成应收计划或登记发货。')
  await page.getByRole('button', {name:'关闭 数据导入',exact:true}).press('Enter')
  await expect(dialog).toBeVisible()
  await page.getByTestId('dialog-confirm').click()
  await saved
  await capture('import-pending')
  await page.getByRole('button', {name:'关闭 数据导入',exact:true}).press('Enter')
  await expect(page.getByRole('tab', {name:'数据导入',exact:true})).toBeVisible()
  releaseResponse()
  await page.getByRole('alert').filter({hasText:'提交结果待核对'}).waitFor()
  await capture('import-lost-response')
  await page.unroute('**/api/import/orders/execute/')
  await page.reload()
  await page.getByRole('tab', {name:'销售订单',exact:true}).click()
  await page.locator('input[type="file"][accept*=".xlsx"]').setInputFiles(workbookPath)
  await expect(page.getByRole('alert').filter({ hasText: '已恢复待核对导入批次' })).toBeVisible()
  const executeResponsePromise = page.waitForResponse(response => new URL(response.url()).pathname === '/api/import/orders/execute/' && response.request().method() === 'POST')
  await page.getByRole('button', {name:'确认导入 1 张草稿',exact:true}).click()
  await page.getByTestId('dialog-confirm').click()
  const executeResponse = await executeResponsePromise
  expect(executeResponse.status()).toBe(200)
  const result = await executeResponse.json()
  expect(result.batch_id).toBe(savedResult.batch_id)
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

  await capture('import-idempotent-success')
  await writeFile(path.join(evidenceDir, 'p1-05-result.json'), JSON.stringify({
    source: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
    result, retryStatus: executeResponse.status(), originalBatch: savedResult.batch_id,
    lookupStatus: resultLookup.status(), errorCsvContainsInvalidSku: csvText.includes(fixture.invalid_sku),
  }, null, 2))
})
