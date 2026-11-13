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

let sharedFixture
for (const [width, height] of [[1366, 768], [1920, 1080]]) {
test('order deletion locks the row until a failed request can be retried ' + width, async ({ page, browser }, testInfo) => {
  const root = new URL('../../', import.meta.url)
  const fixture = width === 1366 ? JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [
    fileURLToPath(new URL('docs/uat-evidence/sales-state-closeout-05/seed.py', root)),
  ], { cwd: fileURLToPath(new URL('backend/', root)), encoding: 'utf8' })) : sharedFixture
  sharedFixture = fixture
  const id = width === 1366 ? fixture.identifiers.draft : fixture.confirmOrders[0]
  const number = width === 1366 ? fixture.orders.draft : 'S5-CONFIRM-1'
  await page.setViewportSize({ width, height })
  await page.goto('/orders?search=' + number)
  const remove = page.getByRole('button', { name: '删除 ' + number })
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
  expect(box.y + box.height).toBeLessThan(height)
  expect(box.x + box.width).toBeLessThanOrEqual(width)
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
    browser: browser.version(), id, requests, width, height,
    screenshotSha256: createHash('sha256').update(screenshot).digest('hex'),
  }, null, 2))
})

test('first bank-event load displays progress and supports retry ' + width, async ({ page }, testInfo) => {
  let release
  const wait = new Promise(resolve => { release = resolve })
  let requests = 0
  await page.route('**/api/rmb-cash-events/**', async route => {
    if (++requests > 6) return route.continue()
    await wait
    await route.fulfill({ status: 503, json: { detail: '合成故障' } })
  })
  await page.setViewportSize({ width, height })
  await page.goto('/rmb-cash-events')
  await expect(page.getByText('正在加载…', { exact: true })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('bank-events-loading-1366.png') })
  release()
  const retry = page.getByRole('button', { name: '重试', exact: true })
  await expect(retry).toBeVisible({ timeout: 12000 })
  await page.screenshot({ path: testInfo.outputPath('bank-events-error-1366.png') })
  await retry.click()
  await expect(page.getByText('正在加载…', { exact: true })).toBeHidden()
  await expect(page.getByText('合成故障', { exact: true })).toBeHidden()
  expect(requests).toBe(7)
  await page.screenshot({ path: testInfo.outputPath('bank-events-recovered-1366.png') })
})

}
