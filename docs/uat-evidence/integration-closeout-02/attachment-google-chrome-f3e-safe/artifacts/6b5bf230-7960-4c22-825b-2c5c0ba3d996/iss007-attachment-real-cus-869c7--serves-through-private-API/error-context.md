# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: iss007-attachment-real.spec.js >> customer follow-up attachment uploads, reopens, and serves through private API
- Location: browser-tests\iss007-attachment-real.spec.js:41:1

# Error details

```
Error: cdpSession.send: Protocol error (Browser.getBrowserCommandLine): Command line not returned because --enable-automation not set.
```

# Test source

```ts
  1   | import { expect, test } from '@playwright/test'
  2   | import crypto from 'node:crypto'
  3   | import fs from 'node:fs/promises'
  4   | import path from 'node:path'
  5   | 
  6   | const evidenceDir = process.env.ISS007_EVIDENCE_DIR || path.resolve(process.cwd(), '../docs/uat-evidence/r1-pre-uat-iss007-attachment-flow')
  7   | const screenshotDir = path.join(evidenceDir, 'screenshots')
  8   | const httpResults = []
  9   | 
  10  | // The isolated runner intentionally selects its own default channel. This
  11  | // visual acceptance file requires the installed Google Chrome explicitly.
  12  | test.use({ channel: 'chrome' })
  13  | 
  14  | async function responseBytes(response) {
  15  |   const body = await response.body()
  16  |   return { body, sha256: crypto.createHash('sha256').update(body).digest('hex') }
  17  | }
  18  | 
  19  | async function absoluteRequest(page, href) {
  20  |   return page.request.get(new URL(href, process.env.ISS007_BASE_URL || 'http://127.0.0.1:55208').toString())
  21  | }
  22  | 
  23  | test.describe.configure({ mode: 'serial' })
  24  | 
  25  | test.beforeAll(async ({ browser }) => {
  26  |   await fs.mkdir(screenshotDir, { recursive: true })
  27  |   const cdp = await browser.newBrowserCDPSession()
  28  |   const version = await cdp.send('Browser.getVersion')
> 29  |   const command = await cdp.send('Browser.getBrowserCommandLine')
      |                             ^ Error: cdpSession.send: Protocol error (Browser.getBrowserCommandLine): Command line not returned because --enable-automation not set.
  30  |   await cdp.detach()
  31  |   const identity = { channel: 'chrome', version: browser.version(), product: version.product,
  32  |     executable: command.arguments[0], synthetic_data_only: true }
  33  |   await fs.writeFile(path.join(evidenceDir, 'browser-identity.json'), JSON.stringify(identity, null, 2), 'utf8')
  34  |   console.log(`ISS007_BROWSER_IDENTITY=${JSON.stringify(identity)}`)
  35  | })
  36  | 
  37  | test.afterAll(async () => {
  38  |   await fs.writeFile(path.join(evidenceDir, 'http-results.json'), JSON.stringify(httpResults, null, 2), 'utf8')
  39  | })
  40  | 
  41  | test('customer follow-up attachment uploads, reopens, and serves through private API', async ({ page }) => {
  42  |   await page.setViewportSize({ width: 1440, height: 950 })
  43  |   await page.goto('/follow-ups')
  44  |   const row = page.locator('.follow-up-list-table tbody tr').filter({ hasText: 'ISS007 附件上传与重开' })
  45  |   await expect(row).toHaveCount(1)
  46  |   await row.getByRole('button', { name: '编辑跟进记录' }).click()
  47  |   const dialog = page.getByRole('dialog', { name: '编辑跟进记录' })
  48  |   const file = dialog.locator('input[type="file"]')
  49  |   await file.setInputFiles({
  50  |     name: 'ISS007-沟通纪要.txt',
  51  |     mimeType: 'text/plain',
  52  |     buffer: Buffer.from('ISS007 synthetic follow-up attachment\n', 'utf8'),
  53  |   })
  54  |   await expect(dialog).toContainText('ISS007-沟通纪要.txt')
  55  |   await page.screenshot({ path: path.join(screenshotDir, 'follow-up-pending-desktop.png'), fullPage: true })
  56  |   await dialog.getByRole('button', { name: '保存跟进' }).click()
  57  |   await expect(page.locator('.toast')).toContainText('跟进记录已更新')
  58  | 
  59  |   await row.getByRole('button', { name: '编辑跟进记录' }).click()
  60  |   const reopened = page.getByRole('dialog', { name: '编辑跟进记录' })
  61  |   await expect(reopened).toContainText('ISS007-沟通纪要.txt')
  62  |   await expect(reopened).toContainText('已上传')
  63  |   const href = await reopened.locator('.follow-up-attachment-editor-item.saved').filter({ hasText: 'ISS007-沟通纪要.txt' }).first().getByRole('link', { name: '查看' }).getAttribute('href')
  64  |   expect(href).toMatch(/^\/api\/media\//)
  65  |   const attachmentResponse = await absoluteRequest(page, href)
  66  |   const attachmentBytes = await responseBytes(attachmentResponse)
  67  |   httpResults.push({ scenario: 'follow-up-authorized-view', status: attachmentResponse.status(), contentType: attachmentResponse.headers()['content-type'], sha256: attachmentBytes.sha256, bytes: attachmentBytes.body.length })
  68  |   expect(attachmentResponse.status()).toBe(200)
  69  |   expect(attachmentBytes.body.toString('utf8')).toContain('ISS007 synthetic follow-up attachment')
  70  |   await page.screenshot({ path: path.join(screenshotDir, 'follow-up-saved-desktop.png'), fullPage: true })
  71  | 
  72  |   await page.setViewportSize({ width: 390, height: 844 })
  73  |   await page.screenshot({ path: path.join(screenshotDir, 'follow-up-saved-390.png'), fullPage: true })
  74  |   const savedAttachment = reopened.locator('.follow-up-attachment-editor-item.saved').filter({ hasText: 'ISS007-沟通纪要.txt' })
  75  |   await savedAttachment.scrollIntoViewIfNeeded()
  76  |   await expect(savedAttachment.getByRole('link', { name: '查看' })).toBeVisible()
  77  |   await page.screenshot({ path: path.join(screenshotDir, 'follow-up-saved-attachment-390-viewport.png') })
  78  |   await page.setViewportSize({ width: 1440, height: 950 })
  79  |   await savedAttachment.scrollIntoViewIfNeeded()
  80  |   await expect(savedAttachment.getByRole('link', { name: '查看' })).toBeVisible()
  81  |   await page.screenshot({ path: path.join(screenshotDir, 'follow-up-saved-attachment-desktop-viewport.png') })
  82  | })
  83  | 
  84  | test('SKU replacement keeps quote image snapshot and exposes thumbnail', async ({ page }) => {
  85  |   await page.setViewportSize({ width: 1440, height: 950 })
  86  |   const beforeQuote = await page.request.get('/api/quotes/1/')
  87  |   expect(beforeQuote.status()).toBe(200)
  88  |   const beforeQuoteData = await beforeQuote.json()
  89  |   const snapshotHref = beforeQuoteData.items?.[0]?.image
  90  |   expect(snapshotHref).toMatch(/^\/api\/media\/quote-item-images\//)
  91  |   const beforeSnapshotResponse = await absoluteRequest(page, snapshotHref)
  92  |   const beforeSnapshot = await responseBytes(beforeSnapshotResponse)
  93  |   expect(beforeSnapshotResponse.status()).toBe(200)
  94  | 
  95  |   await page.goto('/skus')
  96  |   const row = page.locator('.sku-data-row').filter({ hasText: 'ISS007-SKU001' })
  97  |   await expect(row).toHaveCount(1)
  98  |   await row.getByRole('button', { name: '编辑', exact: true }).click()
  99  |   const dialog = page.getByRole('dialog', { name: '编辑 SKU', exact: true })
  100 |   const imageInput = dialog.locator('input[type="file"]')
  101 |   await imageInput.setInputFiles({
  102 |     name: 'iss007-replacement.gif',
  103 |     mimeType: 'image/gif',
  104 |     buffer: Buffer.from('GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;', 'binary'),
  105 |   })
  106 |   await expect(dialog.getByAltText('SKU 图片预览')).toBeVisible()
  107 |   await page.screenshot({ path: path.join(screenshotDir, 'sku-image-preview-desktop.png'), fullPage: true })
  108 |   await dialog.getByRole('button', { name: '保存 SKU', exact: true }).click()
  109 |   await expect(page.locator('.toast')).toContainText('SKU 已更新')
  110 | 
  111 |   const afterSku = await page.request.get('/api/skus/1/')
  112 |   expect(afterSku.status()).toBe(200)
  113 |   const afterSkuData = await afterSku.json()
  114 |   expect(afterSkuData.image).toMatch(/^\/api\/media\/sku-images\//)
  115 |   const currentImageResponse = await absoluteRequest(page, afterSkuData.image)
  116 |   const currentImage = await responseBytes(currentImageResponse)
  117 |   httpResults.push({ scenario: 'sku-current-image-after-replacement', status: currentImageResponse.status(), contentType: currentImageResponse.headers()['content-type'], sha256: currentImage.sha256, bytes: currentImage.body.length })
  118 |   expect(currentImageResponse.status()).toBe(200)
  119 |   expect(currentImage.sha256).not.toBe(beforeSnapshot.sha256)
  120 | 
  121 |   const thumbnailResponse = await page.request.get('/api/skus/1/thumbnail/')
  122 |   const thumbnail = await responseBytes(thumbnailResponse)
  123 |   httpResults.push({ scenario: 'sku-thumbnail-authorized-view', status: thumbnailResponse.status(), contentType: thumbnailResponse.headers()['content-type'], sha256: thumbnail.sha256, bytes: thumbnail.body.length })
  124 |   expect(thumbnailResponse.status()).toBe(200)
  125 |   expect(thumbnailResponse.headers()['content-type']).toContain('image/webp')
  126 | 
  127 |   const afterQuote = await page.request.get('/api/quotes/1/')
  128 |   const afterQuoteData = await afterQuote.json()
  129 |   const afterSnapshotResponse = await absoluteRequest(page, afterQuoteData.items[0].image)
```