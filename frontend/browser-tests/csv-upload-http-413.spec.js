import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const defaultMaxBytes = 10 * 1024 * 1024
const evidenceRoot = process.env.ISS052_HTTP_413_EVIDENCE_ROOT
  || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../docs/uat-evidence/r1-iss052-http-413-bd324-20261031')

test('real Chrome upload receives HTTP 413 for an oversized CSV without connection reset', async ({ page, browserName }) => {
  const maxBytes = Number(process.env.CSV_IMPORT_MAX_BYTES || defaultMaxBytes)
  const oversized = Buffer.concat([
    Buffer.from('code,name\nCHROME-413,'),
    Buffer.alloc(maxBytes + 256 * 1024, 0x78),
    Buffer.from('\n'),
  ])
  const failedRequests = []
  page.on('requestfailed', request => {
    if (new URL(request.url()).pathname === '/api/import/csv/preview/') {
      failedRequests.push({ url: request.url(), error: request.failure()?.errorText })
    }
  })

  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/import')
  await expect(page.locator('input[type="file"]')).toBeEnabled()
  await page.locator('input[type="file"]').setInputFiles({
    name: 'oversized-http-413.csv',
    mimeType: 'text/csv',
    buffer: oversized,
  })

  const responsePromise = page.waitForResponse(response => {
    return new URL(response.url()).pathname === '/api/import/csv/preview/'
      && response.request().method() === 'POST'
  }, { timeout: 60_000 })
  await page.getByRole('button', { name: '预览并校验', exact: true }).click()
  const response = await responsePromise
  const responseBody = await response.json()

  expect(response.status()).toBe(413)
  expect(responseBody.detail).toContain('CSV 文件超过大小限制')
  expect(failedRequests).toEqual([])
  await expect(page.getByRole('alert')).toContainText('CSV 文件超过大小限制')
  await expect(page.getByText('预览失败，请检查后重试', { exact: true })).toBeVisible()

  const browser = await page.evaluate(() => ({ userAgent: navigator.userAgent, platform: navigator.platform }))
  const screenshotPath = path.join(evidenceRoot, 'screenshots', 'chrome-csv-upload-413.png')
  await mkdir(path.dirname(screenshotPath), { recursive: true })
  await page.screenshot({ path: screenshotPath, fullPage: true })
  await writeFile(
    path.join(evidenceRoot, 'logs', 'chrome-csv-upload-413.json'),
    `${JSON.stringify({
      browserName,
      browser,
      pageUrl: page.url(),
      endpoint: new URL(response.url()).pathname,
      status: response.status(),
      responseBody,
      uploadBytes: oversized.length,
      configuredLimitBytes: maxBytes,
      requestFailures: failedRequests,
      screenshot: path.relative(evidenceRoot, screenshotPath).replaceAll('\\', '/'),
    }, null, 2)}\n`,
    'utf8',
  )
})
