import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

test.beforeEach(({ browserName }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== 'ui-prelaunch-polish-01.spec.js',
    'Run this suite with the dedicated authenticated Chrome isolation profile.')
  expect(browserName).toBe('chromium')
})

test('order deletion locks the row until a failed request can be retried', async ({ page, browser }, testInfo) => {
  const root = new URL('../../', import.meta.url)
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [
    fileURLToPath(new URL('docs/uat-evidence/sales-state-closeout-05/seed.py', root)),
  ], { cwd: fileURLToPath(new URL('backend/', root)), encoding: 'utf8' }))
  const id = fixture.identifiers.draft
  await page.setViewportSize({ width: 1366, height: 768 })
  await page.goto('/orders?search=' + fixture.orders.draft)
  const remove = page.getByRole('button', { name: '删除 ' + fixture.orders.draft })
  const confirm = page.getByTestId('dialog-confirm')
  let requests = 0
  let release
  const blocked = new Promise(resolve => { release = resolve })
  await page.route('**/api/orders/' + id + '/', async route => {
    if (route.request().method() !== 'DELETE') return route.continue()
    if (++requests !== 1) return route.continue()
    await blocked
    await route.fulfill({ status: 503, json: { detail: '合成故障' } })
  })
  await remove.dblclick()
  await confirm.click()
  await expect.poll(() => requests).toBe(1)
  await expect(remove).toBeDisabled()
  const box = await remove.boundingBox()
  expect(box.y + box.height).toBeLessThan(768)
  await page.mouse.dblclick(box.x + box.width / 2, box.y + box.height / 2)
  expect(requests).toBe(1)
  const screenshot = await page.screenshot({ path: testInfo.outputPath('delete-pending-1366.png') })
  release()
  await expect(remove).toBeEnabled()
  expect((await page.request.get('/api/orders/' + id + '/')).ok()).toBe(true)
  await remove.click()
  await confirm.click()
  await expect(remove).toHaveCount(0)
  expect(requests).toBe(2)
  expect((await page.request.get('/api/orders/' + id + '/')).status()).toBe(404)
  await writeFile(testInfo.outputPath('delete.json'), JSON.stringify({
    browser: browser.version(), id, requests, width: 1366, height: 768,
    screenshotSha256: createHash('sha256').update(screenshot).digest('hex'),
  }, null, 2))
})

test('first bank-event load displays progress and supports retry', async ({ page }, testInfo) => {
  let release
  const wait = new Promise(resolve => { release = resolve })
  let requests = 0
  await page.route('**/api/rmb-cash-events/**', async route => {
    if (++requests > 1) return route.continue()
    await wait
    await route.fulfill({ status: 503, json: { detail: '合成故障' } })
  })
  await page.setViewportSize({ width: 1366, height: 768 })
  await page.goto('/rmb-cash-events')
  await expect(page.getByText('正在加载…', { exact: true })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('bank-events-loading-1366.png') })
  release()
  await page.getByRole('button', { name: '重试', exact: true }).click()
  await expect(page.getByText('正在加载…', { exact: true })).toBeHidden()
  await expect(page.getByText('合成故障', { exact: true })).toBeHidden()
  expect(requests).toBe(2)
})
