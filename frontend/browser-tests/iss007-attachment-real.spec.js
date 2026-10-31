import { expect, test } from '@playwright/test'
import crypto from 'node:crypto'
import fs from 'node:fs/promises'
import path from 'node:path'

const evidenceDir = process.env.ISS007_EVIDENCE_DIR || path.resolve(process.cwd(), '../docs/uat-evidence/r1-pre-uat-iss007-attachment-flow')
const screenshotDir = path.join(evidenceDir, 'screenshots')
const httpResults = []

async function responseBytes(response) {
  const body = await response.body()
  return { body, sha256: crypto.createHash('sha256').update(body).digest('hex') }
}

async function absoluteRequest(page, href) {
  return page.request.get(new URL(href, process.env.ISS007_BASE_URL || 'http://127.0.0.1:55208').toString())
}

test.describe.configure({ mode: 'serial' })

test.beforeAll(async () => {
  await fs.mkdir(screenshotDir, { recursive: true })
})

test.afterAll(async () => {
  await fs.writeFile(path.join(evidenceDir, 'http-results.json'), JSON.stringify(httpResults, null, 2), 'utf8')
})

test('customer follow-up attachment uploads, reopens, and serves through private API', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 950 })
  await page.goto('/follow-ups')
  const row = page.locator('.follow-up-list-table tbody tr').filter({ hasText: 'ISS007 附件上传与重开' })
  await expect(row).toHaveCount(1)
  await row.getByRole('button', { name: '编辑跟进记录' }).click()
  const dialog = page.getByRole('dialog', { name: '编辑跟进记录' })
  const file = dialog.locator('input[type="file"]')
  await file.setInputFiles({
    name: 'ISS007-沟通纪要.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('ISS007 synthetic follow-up attachment\n', 'utf8'),
  })
  await expect(dialog).toContainText('ISS007-沟通纪要.txt')
  await page.screenshot({ path: path.join(screenshotDir, 'follow-up-pending-desktop.png'), fullPage: true })
  await dialog.getByRole('button', { name: '保存跟进' }).click()
  await expect(page.locator('.toast')).toContainText('跟进记录已更新')

  await row.getByRole('button', { name: '编辑跟进记录' }).click()
  const reopened = page.getByRole('dialog', { name: '编辑跟进记录' })
  await expect(reopened).toContainText('ISS007-沟通纪要.txt')
  await expect(reopened).toContainText('已上传')
  const href = await reopened.locator('.follow-up-attachment-editor-item.saved').filter({ hasText: 'ISS007-沟通纪要.txt' }).first().getByRole('link', { name: '查看' }).getAttribute('href')
  expect(href).toMatch(/^\/api\/media\//)
  const attachmentResponse = await absoluteRequest(page, href)
  const attachmentBytes = await responseBytes(attachmentResponse)
  httpResults.push({ scenario: 'follow-up-authorized-view', status: attachmentResponse.status(), contentType: attachmentResponse.headers()['content-type'], sha256: attachmentBytes.sha256, bytes: attachmentBytes.body.length })
  expect(attachmentResponse.status()).toBe(200)
  expect(attachmentBytes.body.toString('utf8')).toContain('ISS007 synthetic follow-up attachment')
  await page.screenshot({ path: path.join(screenshotDir, 'follow-up-saved-desktop.png'), fullPage: true })

  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: path.join(screenshotDir, 'follow-up-saved-390.png'), fullPage: true })
})

test('SKU replacement keeps quote image snapshot and exposes thumbnail', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 950 })
  const beforeQuote = await page.request.get('/api/quotes/1/')
  expect(beforeQuote.status()).toBe(200)
  const beforeQuoteData = await beforeQuote.json()
  const snapshotHref = beforeQuoteData.items?.[0]?.image
  expect(snapshotHref).toMatch(/^\/api\/media\/quote-item-images\//)
  const beforeSnapshotResponse = await absoluteRequest(page, snapshotHref)
  const beforeSnapshot = await responseBytes(beforeSnapshotResponse)
  expect(beforeSnapshotResponse.status()).toBe(200)

  await page.goto('/skus')
  const row = page.locator('.sku-data-row').filter({ hasText: 'ISS007-SKU001' })
  await expect(row).toHaveCount(1)
  await row.getByRole('button', { name: '编辑', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '编辑 SKU', exact: true })
  const imageInput = dialog.locator('input[type="file"]')
  await imageInput.setInputFiles({
    name: 'iss007-replacement.gif',
    mimeType: 'image/gif',
    buffer: Buffer.from('GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;', 'binary'),
  })
  await expect(dialog.getByAltText('SKU 图片预览')).toBeVisible()
  await page.screenshot({ path: path.join(screenshotDir, 'sku-image-preview-desktop.png'), fullPage: true })
  await dialog.getByRole('button', { name: '保存 SKU', exact: true }).click()
  await expect(page.locator('.toast')).toContainText('SKU 已更新')

  const afterSku = await page.request.get('/api/skus/1/')
  expect(afterSku.status()).toBe(200)
  const afterSkuData = await afterSku.json()
  expect(afterSkuData.image).toMatch(/^\/api\/media\/sku-images\//)
  const currentImageResponse = await absoluteRequest(page, afterSkuData.image)
  const currentImage = await responseBytes(currentImageResponse)
  httpResults.push({ scenario: 'sku-current-image-after-replacement', status: currentImageResponse.status(), contentType: currentImageResponse.headers()['content-type'], sha256: currentImage.sha256, bytes: currentImage.body.length })
  expect(currentImageResponse.status()).toBe(200)
  expect(currentImage.sha256).not.toBe(beforeSnapshot.sha256)

  const thumbnailResponse = await page.request.get('/api/skus/1/thumbnail/')
  const thumbnail = await responseBytes(thumbnailResponse)
  httpResults.push({ scenario: 'sku-thumbnail-authorized-view', status: thumbnailResponse.status(), contentType: thumbnailResponse.headers()['content-type'], sha256: thumbnail.sha256, bytes: thumbnail.body.length })
  expect(thumbnailResponse.status()).toBe(200)
  expect(thumbnailResponse.headers()['content-type']).toContain('image/webp')

  const afterQuote = await page.request.get('/api/quotes/1/')
  const afterQuoteData = await afterQuote.json()
  const afterSnapshotResponse = await absoluteRequest(page, afterQuoteData.items[0].image)
  const afterSnapshot = await responseBytes(afterSnapshotResponse)
  httpResults.push({ scenario: 'quote-historical-image-after-sku-replacement', status: afterSnapshotResponse.status(), contentType: afterSnapshotResponse.headers()['content-type'], sha256: afterSnapshot.sha256, bytes: afterSnapshot.body.length })
  expect(afterSnapshotResponse.status()).toBe(200)
  expect(afterSnapshot.sha256).toBe(beforeSnapshot.sha256)

  await page.goto('/quotes')
  await expect(page.locator('body')).toContainText('ISS007-Q001')
  await page.screenshot({ path: path.join(screenshotDir, 'quote-image-snapshot-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: path.join(screenshotDir, 'quote-image-snapshot-390.png'), fullPage: true })
})

test('attachment upload failure stays visible and retries without duplicating the follow-up', async ({ page }) => {
  await page.route('**/api/follow-ups/1/attachments/', route => route.abort('failed'))
  await page.goto('/follow-ups')
  const row = page.locator('.follow-up-list-table tbody tr').filter({ hasText: 'ISS007 附件上传与重开' })
  await row.getByRole('button', { name: '编辑跟进记录' }).click()
  const dialog = page.getByRole('dialog', { name: '编辑跟进记录' })
  await dialog.locator('input[type="file"]').setInputFiles({ name: 'ISS007-failure-retry.txt', mimeType: 'text/plain', buffer: Buffer.from('retry') })
  await dialog.getByRole('button', { name: '保存跟进' }).click()
  await expect(page.locator('.toast')).toContainText('记录已保存，但网络连接失败')
  const dialogCountAfterFailure = await page.getByRole('dialog', { name: '编辑跟进记录' }).count()
  const retryControlVisible = Boolean(dialogCountAfterFailure && await page.getByRole('dialog', { name: '编辑跟进记录' }).getByText('待上传').count())
  httpResults.push({ scenario: 'follow-up-upload-failure', status: 'browser-route-aborted', dialogCountAfterFailure, retryControlVisible })
  await page.screenshot({ path: path.join(screenshotDir, 'follow-up-upload-failure.png'), fullPage: true })
  expect(dialogCountAfterFailure).toBe(1)
  expect(retryControlVisible).toBeTruthy()
  await page.unroute('**/api/follow-ups/1/attachments/')
  await dialog.getByRole('button', { name: '保存跟进' }).click()
  await expect(page.locator('.toast')).toContainText('跟进记录已更新')
  await row.getByRole('button', { name: '编辑跟进记录' }).click()
  await expect(page.getByRole('dialog', { name: '编辑跟进记录' })).toContainText('ISS007-failure-retry.txt')
  await page.screenshot({ path: path.join(screenshotDir, 'follow-up-upload-retry-success.png'), fullPage: true })
})
