import { execFileSync } from 'node:child_process'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const file = 'small-team-history-snapshot.spec.js'
test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== file, 'Requires the dedicated codex fixture.')

test('historical carton quantity rejects fractions and reads back the original receivable', async ({ page, baseURL }) => {
  test.setTimeout(180000)
  const repository = fileURLToPath(new URL('../../', import.meta.url))
  const seed = path.join(repository, 'docs/uat-evidence/small-team-cancel-refund-01/seed-history.py')
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.join(repository, 'backend'), encoding: 'utf8', env: { ...process.env, PYTHONUTF8: '1' },
  }))
  const output = path.join(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'history-snapshot')
  await mkdir(output, { recursive: true })
  const cdp = await page.context().newCDPSession(page)
  expect((await cdp.send('Browser.getVersion')).product).toMatch(/^Chrome\//)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto(new URL('/orders?search=' + fixture.number, baseURL).href)
  const row = page.locator('.workspace-pane:not([aria-hidden=true]) .order-list-table tbody tr').filter({ hasText: fixture.number })
  await row.click()
  const workbench = page.getByRole('dialog', { name: '订单工作台' })
  await workbench.getByRole('button', { name: '调整数量', exact: true }).click()
  const editor = page.getByRole('dialog', { name: '调整订单数量' })
  await expect(editor).toContainText('5.00')
  await editor.getByLabel('变更原因').fill('核对历史整箱接续变更')
  const quantity = editor.getByRole('spinbutton', { name: /新的交易数量/ })
  await quantity.fill('5.5')
  const previewButton = editor.getByRole('button', { name: '预览影响' })
  const previewResponse = () => page.waitForResponse(response => response.url().endsWith('/quantity-adjustments/preview/') && response.request().method() === 'POST')
  const [rejected] = await Promise.all([previewResponse(), previewButton.click()])
  expect(rejected.status()).toBe(400)
  await expect(editor).toContainText('只允许整包装数量')
  await editor.screenshot({ path: path.join(output, 'fraction-rejected.png') })
  await quantity.fill('6')
  const [accepted] = await Promise.all([previewResponse(), previewButton.click()])
  expect(accepted.status()).toBe(200)
  const preview = editor.locator('.quantity-adjustment-preview')
  await expect(preview).toContainText('16.75')
  await expect(preview).toContainText('20.10')
  await expect(preview).toContainText('3.35')
  await editor.screenshot({ path: path.join(output, 'preview.png') })
  await editor.getByRole('button', { name: '确认调整' }).click()
  const [saved] = await Promise.all([
    page.waitForResponse(response => response.url().endsWith('/quantity-adjustments/') && response.request().method() === 'POST'),
    page.getByRole('button', { name: '确认提交', exact: true }).click(),
  ])
  expect(saved.status()).toBe(201)
  await expect(editor).toBeHidden()
  await workbench.getByRole('button', { name: '关闭订单详情' }).click()
  await row.click()
  await expect(workbench.locator('.quantity-adjustment-history')).toContainText('核对历史整箱接续变更')
  const detail = await (await page.request.get('/api/orders/' + fixture.order + '/workbench/')).json()
  expect(Number(detail.items[0].quantity)).toBe(60)
  expect(Number(detail.items[0].trade_quantity)).toBe(6)
  expect(Number(detail.order.total_amount)).toBe(20.10)
  const original = await (await page.request.get('/api/orders/' + fixture.original + '/')).json()
  expect(Number(original.balance_amount)).toBe(20.10)
  await workbench.screenshot({ path: path.join(output, 'reopened.png') })
})
