import { execFileSync } from 'node:child_process'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

test('cancel a paid order and refund 400 then 600 from its original receipt', async ({ page, baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== 'small-team-paid-cancel.spec.js', 'Requires isolated seed')
  test.setTimeout(180000)
  const repo = fileURLToPath(new URL('../../', import.meta.url))
  const seed = path.join(repo, 'docs/uat-evidence/small-team-cancel-refund-01/seed-paid-cancel.py')
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.join(repo, 'backend'), encoding: 'utf8', env: { ...process.env, PYTHONUTF8: '1' },
  }))
  const output = path.join(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'paid-cancel')
  await mkdir(output, { recursive: true })
  const cdp = await page.context().newCDPSession(page)
  expect((await cdp.send('Browser.getVersion')).product).toMatch(/^Chrome\//)
  await page.setViewportSize({ width: 1440, height: 900 })
  const workbench = page.getByRole('dialog', { name: '订单工作台' })
  const openOrder = async () => {
    await page.goto(new URL('/orders?search=' + fixture.number, baseURL).href)
    await page.getByRole('row').filter({ hasText: fixture.number }).click()
    await expect(workbench).toBeVisible()
  }
  await openOrder()
  await workbench.getByRole('button', { name: '取消订单', exact: true }).click()
  await page.getByLabel('取消原因').fill('合成取消后按原收款分次退款')
  await page.getByRole('button', { name: '确认取消', exact: true }).click()
  await expect(workbench.locator('.payment-card')).toContainText(/待退款.*1,000\.00/)
  await workbench.screenshot({ path: path.join(output, 'cancelled.png') })
  for (const [amount, remaining] of [[400, 600], [600, 0]]) {
    await page.goto(new URL('/transactions?search=' + fixture.receiptNo, baseURL).href)
    await page.getByRole('row').filter({ hasText: fixture.receiptNo }).getByRole('button', { name: '详情', exact: true }).click()
    await page.getByRole('button', { name: '从本笔登记退款' }).click()
    const form = page.getByRole('dialog', { name: '登记退款' })
    await form.getByLabel('退款对应订单').selectOption(String(fixture.order))
    await form.getByLabel(/实际退款金额/).fill(String(amount))
    await form.getByLabel('退款依据').fill('核对本次合成退款凭证 ' + amount)
    await form.getByLabel('实际退款凭证').setInputFiles({
      name: 'refund-' + amount + '.pdf', mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4\nSynthetic refund ' + amount + '\n%%EOF'),
    })
    await form.getByRole('button', { name: '上传凭证', exact: true }).click()
    await expect(form.getByText(/凭证已上传/)).toBeVisible()
    const saved = page.waitForResponse(r => r.url().endsWith('/refund-cash/') && r.request().method() === 'POST')
    await form.getByRole('button', { name: '确认登记' }).click()
    const response = await saved
    expect(response.status(), await response.text()).toBe(201)
    await expect(form).toBeHidden()
    await openOrder()
    const payment = workbench.locator('.payment-card')
    if (remaining) await expect(payment).toContainText(/待退款.*600\.00/)
    else await expect(payment).not.toContainText('待退款')
    await workbench.screenshot({ path: path.join(output, 'remaining-' + remaining + '.png') })
  }
  const receipt = await (await page.request.get('/api/transactions/' + fixture.receipt + '/')).json()
  expect(receipt.status).toBe('confirmed')
  expect(receipt.receipt_refunds.map(item => Number(item.amount)).sort()).toEqual([400, 600])
})
