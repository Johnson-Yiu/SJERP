import { execFileSync } from 'node:child_process'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const file = 'small-team-quantity-finance-01.spec.js'
test.use({ headless: false })
test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== file, 'Use the dedicated isolated Chrome profile.')

test('quantity changes retain exact receivable and net cash after reopening', async ({ page, baseURL }) => {
  test.setTimeout(90000)
  expect(process.env.ISOLATED_CODEX_TEST_SUPERADMIN).toBe('1')
  const session = await page.request.get('/api/session/current-operator/')
  expect(await session.json()).toMatchObject({ name: 'codex', authenticated: true })
  const cdp = await page.context().newCDPSession(page)
  expect((await cdp.send('Browser.getVersion')).product).toMatch(/^Chrome\//)

  const repository = fileURLToPath(new URL('../../', import.meta.url))
  const evidence = path.join(repository, 'docs/uat-evidence/small-team-quantity-finance-01')
  const cases = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [path.join(evidence, 'seed.py')], {
    cwd: path.join(repository, 'backend'), encoding: 'utf8',
  }))
  const screenshots = path.join(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT || evidence, 'screenshots')
  await mkdir(screenshots, { recursive: true })
  await page.setViewportSize({ width: 1440, height: 900 })
  const workbench = page.getByRole('dialog', { name: '订单工作台' })
  const dialog = page.getByRole('dialog', { name: '调整订单数量' })
  const activeRows = page.locator('.workspace-pane:not([aria-hidden=true]) .order-list-table tbody tr')
  for (const scenario of [
    { case: 'CENTS', quantity: '2', total: '0.67', delta: '0.33', paid: '0.00', balance: '0.67' },
    { case: 'FEE', quantity: '11', total: '1100.00', delta: '100.00', paid: '980.00', balance: '100.00' },
  ]) {
    const fixture = cases[scenario.case]
    await page.goto(new URL('/orders?search=' + fixture.number, baseURL).href, { waitUntil: 'domcontentloaded' })
    const row = activeRows.filter({ hasText: fixture.number })
    await row.click()
    if (scenario.case === 'FEE') await expect(workbench.locator('.cost-profit-card')).toContainText('采购合同调整')
    await workbench.getByRole('button', { name: '调整数量', exact: true }).click()
    await dialog.getByRole('spinbutton', { name: /新的基础数量/ }).fill(scenario.quantity)
    await dialog.getByLabel('变更原因').fill('核对数量变更后的订单金额与待收')
    await dialog.getByRole('button', { name: '预览影响' }).click()
    const preview = dialog.locator('.quantity-adjustment-preview')
    await expect(preview).toContainText(scenario.delta)
    await expect(preview).toContainText('调整后待收 USD ' + scenario.balance)
    if (scenario.case === 'FEE') await expect(preview).toContainText('已核销含我方承担手续费 USD 20.00')
    await dialog.screenshot({ path: path.join(screenshots, scenario.case + '-preview.png') })
    await dialog.getByRole('button', { name: '确认调整' }).click()
    const save = page.waitForResponse(response => response.url().endsWith('/quantity-adjustments/') && response.request().method() === 'POST')
    await page.getByRole('button', { name: '确认提交', exact: true }).click()
    expect((await save).status()).toBe(201)
    await expect(dialog).toBeHidden()
    await workbench.getByRole('button', { name: '关闭订单详情' }).click()
    await row.click()
    await expect(workbench.locator('.quantity-adjustment-history')).toContainText('核对数量变更后的订单金额与待收')
    const payment = workbench.locator('.payment-card')
    await expect(payment).toContainText('USD ' + Number(scenario.total).toLocaleString('en-US', { minimumFractionDigits: 2 }))
    await expect(payment).toContainText('USD ' + scenario.paid)
    await expect(payment).toContainText('USD ' + scenario.balance)
    const saved = await page.request.get('/api/orders/' + fixture.id + '/workbench/')
    const detail = await saved.json()
    expect(Number(detail.order.total_amount)).toBe(Number(scenario.total))
    expect(Number(detail.payment_summary.planned_amount)).toBe(Number(scenario.total))
    expect(Number(detail.payment_summary.paid_amount)).toBe(Number(scenario.paid))
    expect(Number(detail.payment_summary.balance_amount)).toBe(Number(scenario.balance))
    await payment.screenshot({ path: path.join(screenshots, scenario.case + '-reopened.png') })
    await workbench.getByRole('button', { name: '关闭订单详情' }).click()
  }
  await page.goto(new URL('/orders?search=' + cases.INCOMPLETE.number, baseURL).href, { waitUntil: 'domcontentloaded' })
  await activeRows.filter({ hasText: cases.INCOMPLETE.number }).click()
  const cost = workbench.locator('.cost-profit-card')
  await expect(cost).toContainText('成本待核实')
  await expect(cost).not.toContainText('¥')
  await expect(workbench).toContainText(cases.INCOMPLETE.number)
  await cost.screenshot({ path: path.join(screenshots, 'incomplete-cost.png') })

})
