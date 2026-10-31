import { spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { expect, test } from '@playwright/test'

const evidenceDir = process.env.ISS007_EVIDENCE_DIR
const repositoryRoot = path.resolve(process.cwd(), '..')
const backendRoot = path.join(repositoryRoot, 'backend')
const fixturePath = path.join(evidenceDir, 'fixture.json')

function sha256(value) {
  return createHash('sha256').update(value).digest('hex')
}

function pythonEvidence(stage, workbookPath) {
  const args = [path.join(backendRoot, 'verify_iss007_image_browser.py'), '--stage', stage]
  if (workbookPath) args.push('--workbook', workbookPath)
  const result = spawnSync(process.env.ISOLATED_TEST_PYTHON, args, {
    cwd: backendRoot,
    encoding: 'utf8',
    env: process.env,
  })
  if (result.status !== 0) throw new Error(`Database evidence ${stage} failed: ${result.stdout}\n${result.stderr}`)
  return JSON.parse(result.stdout)
}

async function apiJson(page, method, url, body) {
  return page.evaluate(async ({ method, url, body }) => {
    const response = await fetch(url, {
      method,
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    const text = await response.text()
    let data
    try { data = text ? JSON.parse(text) : null } catch { data = text }
    return { status: response.status, data }
  }, { method, url, body })
}

async function openSkuEditor(page, skuCode) {
  const row = page.locator('.sku-data-row').filter({ hasText: skuCode })
  await expect(row).toBeVisible()
  await row.getByTitle('编辑').click()
  return page.getByRole('dialog', { name: '编辑 SKU' })
}

async function selectImageAndSave(page, dialog, name, buffer) {
  await dialog.locator('input[type="file"]').setInputFiles({ name, mimeType: 'image/png', buffer })
  await expect(dialog.locator('.sku-image-preview')).toBeVisible()
  await dialog.getByRole('button', { name: '保存 SKU', exact: true }).click()
}

async function quoteImageFromApi(page, quoteId) {
  const result = await apiJson(page, 'GET', `/api/quotes/${quoteId}/pi-data/`)
  expect(result.status, JSON.stringify(result.data)).toBe(200)
  expect(result.data.products[0].image_url).toContain('/api/media/quote-item-images/')
  const response = await page.request.get(new URL(result.data.products[0].image_url, page.url()).href)
  return { response, bytes: await response.body(), data: result.data }
}

async function openQuotePreview(page, quoteId) {
  await page.goto(`/quotes?detail=${quoteId}`)
  const workbench = page.getByRole('dialog', { name: '报价工作台' })
  await expect(workbench).toBeVisible()
  await workbench.getByRole('button', { name: '预览 PI' }).first().click()
  const preview = page.getByRole('dialog', { name: '报价单预览' })
  await expect(preview).toBeVisible()
  return preview
}

test('ISS-007 SKU image upload, immutable quote/order snapshots, exports, and missing private images', async ({ page }) => {
  test.setTimeout(60_000)
  if (!evidenceDir || !process.env.ISOLATED_TEST_PYTHON) throw new Error('Isolated ISS-007 evidence configuration is missing.')
  await mkdir(path.join(evidenceDir, 'screenshots'), { recursive: true })
  await mkdir(path.join(evidenceDir, 'exports'), { recursive: true })
  const fixture = JSON.parse(await readFile(fixturePath, 'utf8'))
  const originalBytes = Buffer.from(fixture.original_image_base64, 'base64')
  const replacementBytes = Buffer.from(fixture.replacement_image_base64, 'base64')
  expect(sha256(originalBytes)).toBe(fixture.original_image_sha256)
  expect(sha256(replacementBytes)).toBe(fixture.replacement_image_sha256)
  const pageErrors = []
  const imageResponses = []
  const mediaResponses = []
  page.on('pageerror', error => pageErrors.push(error.message))
  page.on('response', response => {
    if (response.url().includes('/api/skus/') && response.url().includes('/image/')) {
      imageResponses.push({ status: response.status(), url: new URL(response.url()).pathname })
    }
    if (response.url().includes('/api/media/')) {
      mediaResponses.push({ status: response.status(), url: new URL(response.url()).pathname })
    }
  })

  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/skus')
  await expect(page.getByRole('heading', { name: 'SKU 管理', exact: true, level: 2 })).toBeVisible()
  let dialog = await openSkuEditor(page, fixture.sku_code)
  await selectImageAndSave(page, dialog, 'iss007-original-red.png', originalBytes)
  await expect(dialog).toHaveCount(0)

  let row = page.locator('.sku-data-row').filter({ hasText: fixture.sku_code })
  let thumbnail = row.locator('img.sku-table-thumbnail')
  await expect(thumbnail).toBeVisible()
  await expect(thumbnail).toHaveJSProperty('naturalWidth', 48)
  await page.screenshot({ path: path.join(evidenceDir, 'screenshots', 'sku-image-upload-desktop-1440.png'), fullPage: true })

  const initialSkuResponse = await apiJson(page, 'GET', `/api/skus/${fixture.sku_id}/`)
  expect(initialSkuResponse.status).toBe(200)
  const thumbnailResponse = await page.request.get(new URL(initialSkuResponse.data.image_thumbnail, page.url()).href)
  expect(thumbnailResponse.status()).toBe(200)
  expect(thumbnailResponse.headers()['content-type']).toContain('image/webp')

  const quoteCreate = await apiJson(page, 'POST', '/api/quotes/', {
    customer: fixture.customer_id,
    quote_date: '2026-10-31',
    valid_until: '2026-11-30',
    currency: 'USD',
    items: [{ sku: fixture.sku_id, quantity: '2.00', unit_price: '12.50', description: 'ISS-007 synthetic red image snapshot' }],
  })
  expect(quoteCreate.status, JSON.stringify(quoteCreate.data)).toBe(201)
  fixture.quote_id = quoteCreate.data.id
  fixture.quote_no = quoteCreate.data.quote_no
  const savedQuote = await apiJson(page, 'GET', `/api/quotes/${fixture.quote_id}/`)
  expect(savedQuote.status).toBe(200)
  fixture.quote_item_id = savedQuote.data.items[0].id
  const accept = await apiJson(page, 'POST', `/api/quotes/${fixture.quote_id}/accept/`, {})
  expect(accept.status, JSON.stringify(accept.data)).toBe(200)
  const orderDraft = await apiJson(page, 'GET', `/api/quotes/${fixture.quote_id}/order-draft/`)
  expect(orderDraft.status, JSON.stringify(orderDraft.data)).toBe(200)
  const orderCreate = await apiJson(page, 'POST', '/api/orders/', orderDraft.data)
  expect(orderCreate.status, JSON.stringify(orderCreate.data)).toBe(201)
  fixture.order_id = orderCreate.data.id
  fixture.order_no = orderCreate.data.order_no
  const orderDetail = await apiJson(page, 'GET', `/api/orders/${fixture.order_id}/`)
  fixture.order_item_id = orderDetail.data.items[0].id
  const confirm = await apiJson(page, 'POST', `/api/orders/${fixture.order_id}/confirm/`, {})
  expect(confirm.status, JSON.stringify(confirm.data)).toBe(200)
  expect(confirm.data.status).toBe('confirmed')
  await writeFile(fixturePath, `${JSON.stringify(fixture, null, 2)}\n`, 'utf8')

  const originalQuoteImage = await quoteImageFromApi(page, fixture.quote_id)
  expect(originalQuoteImage.response.status()).toBe(200)
  expect(sha256(originalQuoteImage.bytes)).toBe(fixture.original_image_sha256)
  const databaseBefore = pythonEvidence('before')
  expect(databaseBefore.confirmed_order.status).toBe('confirmed')
  expect(databaseBefore.formal_quote.image_snapshot_sha256).toBe(fixture.original_image_sha256)

  const formalQuotePreview = await openQuotePreview(page, fixture.quote_id)
  const previewImage = formalQuotePreview.locator('.pi-image-frame img').first()
  await expect(previewImage).toBeVisible()
  await expect.poll(() => previewImage.evaluate(image => image.naturalWidth)).toBe(48)
  await page.screenshot({ path: path.join(evidenceDir, 'screenshots', 'quote-pi-original-snapshot-desktop-1440.png'), fullPage: true })
  await formalQuotePreview.getByRole('button', { name: '关闭预览' }).click()
  const workbench = page.getByRole('dialog', { name: '报价工作台' })
  const downloadPromise = page.waitForEvent('download')
  await workbench.getByRole('button', { name: '导出 Excel' }).click()
  const download = await downloadPromise
  const workbookPath = path.join(evidenceDir, 'exports', 'iss007-formal-quote-pi.xlsx')
  await download.saveAs(workbookPath)

  await page.goto('/skus')
  dialog = await openSkuEditor(page, fixture.sku_code)
  await dialog.locator('input[type="file"]').setInputFiles({ name: 'invalid.png', mimeType: 'image/png', buffer: Buffer.from('not a png image') })
  await dialog.getByRole('button', { name: '保存 SKU', exact: true }).click()
  await expect(dialog.getByRole('alert')).toContainText('图片上传失败')
  expect(imageResponses.some(response => response.status === 400)).toBeTruthy()
  let currentSku = await apiJson(page, 'GET', `/api/skus/${fixture.sku_id}/`)
  let currentImage = await page.request.get(new URL(currentSku.data.image, page.url()).href)
  expect(currentImage.status()).toBe(200)
  expect(sha256(await currentImage.body())).toBe(fixture.original_image_sha256)

  await dialog.locator('input[type="file"]').setInputFiles({ name: 'iss007-replacement-blue.png', mimeType: 'image/png', buffer: replacementBytes })
  await dialog.getByRole('button', { name: '重试上传图片', exact: true }).click()
  await expect(dialog).toHaveCount(0)
  expect(imageResponses.some(response => response.status === 200)).toBeTruthy()

  currentSku = await apiJson(page, 'GET', `/api/skus/${fixture.sku_id}/`)
  expect(currentSku.status).toBe(200)
  currentImage = await page.request.get(new URL(currentSku.data.image, page.url()).href)
  expect(currentImage.status()).toBe(200)
  expect(sha256(await currentImage.body())).toBe(fixture.replacement_image_sha256)
  row = page.locator('.sku-data-row').filter({ hasText: fixture.sku_code })
  thumbnail = row.locator('img.sku-table-thumbnail')
  await expect(thumbnail).toBeVisible()
  await expect(thumbnail).toHaveJSProperty('naturalWidth', 48)
  await page.screenshot({ path: path.join(evidenceDir, 'screenshots', 'sku-image-replaced-desktop-1440.png'), fullPage: true })

  const quoteAfterReplacement = await quoteImageFromApi(page, fixture.quote_id)
  expect(quoteAfterReplacement.response.status()).toBe(200)
  expect(sha256(quoteAfterReplacement.bytes)).toBe(fixture.original_image_sha256)
  const orderAfterReplacement = await apiJson(page, 'GET', `/api/orders/${fixture.order_id}/`)
  expect(orderAfterReplacement.status).toBe(200)
  expect(orderAfterReplacement.data.status).toBe('confirmed')
  expect(orderAfterReplacement.data.quote).toBeTruthy()
  expect(orderAfterReplacement.data.items[0].sku_code).toBe(fixture.sku_code)
  const databaseAfter = pythonEvidence('after', workbookPath)
  expect(databaseAfter.confirmed_order.linked_quote_image_snapshot_sha256).toBe(fixture.original_image_sha256)
  expect(databaseAfter.export.original_snapshot_embedded).toBeTruthy()

  const finalQuotePreview = await openQuotePreview(page, fixture.quote_id)
  const finalImage = finalQuotePreview.locator('.pi-image-frame img').first()
  await expect.poll(() => finalImage.evaluate(image => image.naturalWidth)).toBe(48)
  await page.screenshot({ path: path.join(evidenceDir, 'screenshots', 'quote-pi-after-sku-replacement-desktop-1440.png'), fullPage: true })
  await finalQuotePreview.getByRole('button', { name: '关闭预览' }).click()

  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/skus')
  row = page.locator('.sku-data-row').filter({ hasText: fixture.sku_code })
  await expect(row.locator('img.sku-table-thumbnail')).toBeVisible()
  await page.screenshot({ path: path.join(evidenceDir, 'screenshots', 'sku-image-replaced-mobile-390.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()

  const mobilePreview = await openQuotePreview(page, fixture.quote_id)
  const mobileImage = mobilePreview.locator('.pi-image-frame img').first()
  await expect.poll(() => mobileImage.evaluate(image => image.naturalWidth)).toBe(48)
  await page.screenshot({ path: path.join(evidenceDir, 'screenshots', 'quote-pi-history-mobile-390.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  await mobilePreview.getByRole('button', { name: '关闭预览' }).click()

  const missingPi = await apiJson(page, 'GET', `/api/quotes/${fixture.missing_quote_id}/pi-data/`)
  expect(missingPi.status).toBe(200)
  const missingMedia = await page.request.get(new URL(missingPi.data.products[0].image_url, page.url()).href)
  expect(missingMedia.status()).toBe(404)
  const missingPreview = await openQuotePreview(page, fixture.missing_quote_id)
  const missingImage = missingPreview.locator('.pi-image-frame img').first()
  await expect(missingImage).toBeVisible()
  await expect.poll(() => missingImage.evaluate(image => image.complete && image.naturalWidth === 0)).toBeTruthy()
  await expect(missingPreview.locator('.pi-product-row')).toContainText('用于验证历史图片文件缺失时页面仍可用')
  await page.screenshot({ path: path.join(evidenceDir, 'screenshots', 'missing-history-image-mobile-390.png'), fullPage: true })
  expect(pageErrors).toEqual([])
  expect(imageResponses.some(response => response.status === 400)).toBeTruthy()
  expect(imageResponses.filter(response => response.status === 200).length).toBeGreaterThanOrEqual(2)

  const browserResults = {
    viewport: { desktop: '1440x1000', narrow: '390x844' },
    sku_image_upload_thumbnail_visible: true,
    invalid_image_http_status: imageResponses.find(response => response.status === 400)?.status,
    sku_image_replacement_http_status: imageResponses.find(response => response.status === 200)?.status,
    original_sku_image_sha256: fixture.original_image_sha256,
    replacement_sku_image_sha256: fixture.replacement_image_sha256,
    historical_quote_image_sha256_after_replacement: sha256(quoteAfterReplacement.bytes),
    confirmed_order_status_after_replacement: orderAfterReplacement.data.status,
    exported_workbook: path.relative(repositoryRoot, workbookPath),
    missing_history_image_page_errors: pageErrors,
    missing_history_image_http_status: missingMedia.status(),
    database_before: databaseBefore,
    database_after: databaseAfter,
    screenshots: [
      'sku-image-upload-desktop-1440.png', 'quote-pi-original-snapshot-desktop-1440.png',
      'sku-image-replaced-desktop-1440.png', 'quote-pi-after-sku-replacement-desktop-1440.png',
      'sku-image-replaced-mobile-390.png', 'quote-pi-history-mobile-390.png', 'missing-history-image-mobile-390.png',
    ],
  }
  await writeFile(path.join(evidenceDir, 'browser-results.json'), `${JSON.stringify(browserResults, null, 2)}\n`, 'utf8')
})
