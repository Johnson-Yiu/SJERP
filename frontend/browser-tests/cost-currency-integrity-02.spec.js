import { test, expect } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

test.use({ channel: 'chrome', viewport: { width: 1366, height: 768 } })
test('manual continuation cost saves and reloads independently of SKU sales currency', async ({ page, browser }, info) => {
  const baseline = process.env.COST_BASELINE === '1'
  test.setTimeout(180_000)
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [
    path.resolve('../docs/uat-evidence/cost-currency-integrity-02/seed-browser.py'),
  ], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' }).trim().split('\n').at(-1))
  const output = info.outputPath('cost-currency')
  await mkdir(output, { recursive: true })
  await page.goto('/history-takeover?application=' + fixture.application)
  await page.getByText('未结余额与剩余业务', { exact: true }).click()
  await page.getByRole('button', { name: '读取合同与未结来源' }).click()
  const currency = page.getByLabel(baseline ? '成本币种（SKU：USD）' : '成本币种（SKU 参考：CNY）')
  await expect(currency).toHaveValue(baseline ? 'USD' : 'EUR')
  await expect(page.getByLabel('核实单位成本', { exact: true })).toHaveValue('7.1250')
  await currency.scrollIntoViewIfNeeded()
  await page.screenshot({ path: path.join(output, 'before-save.png') })
  await currency.fill(baseline ? 'EUR' : 'USD')
  await page.getByLabel('核实单位成本', { exact: true }).fill('9.3750')
  await page.getByLabel('成本依据', { exact: true }).fill('synthetic://browser-USD-cost')
  const saved = page.waitForResponse(r => r.url().includes('/operational-propose/') && r.request().method() === 'POST')
  await page.getByRole('button', { name: '保存接续申请', exact: true }).click()
  const response = await saved
  if (baseline) {
    expect(response.status()).toBe(400)
    await currency.scrollIntoViewIfNeeded()
    await page.screenshot({ path: path.join(output, 'baseline-rejected-independent-cost.png') })
    await writeFile(path.join(output, 'result.json'), JSON.stringify({ source: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
      browser: browser.version(), viewport: page.viewportSize(), devicePixelRatio: await page.evaluate(() => devicePixelRatio),
      saveStatus: response.status(), error: await response.json(), fixture, baseline: true }, null, 2))
    return
  }
  expect(response.status()).toBe(200)
  await page.reload()
  await page.getByText('未结余额与剩余业务', { exact: true }).click()
  const reloaded = page.waitForResponse(r => r.url().includes('/operational-status/') && r.request().method() === 'POST')
  await page.getByRole('button', { name: '读取合同与未结来源' }).click()
  await expect(currency).toHaveValue('USD')
  await expect(page.getByLabel('核实单位成本', { exact: true })).toHaveValue('9.3750')
  await expect(page.getByLabel('成本依据', { exact: true })).toHaveValue('synthetic://browser-USD-cost')
  await currency.scrollIntoViewIfNeeded()
  await page.screenshot({ path: path.join(output, 'saved-reopened.png') })
  await page.setViewportSize({ width: 1920, height: 1080 })
  await currency.scrollIntoViewIfNeeded()
  await page.screenshot({ path: path.join(output, 'saved-reopened-1920.png') })
  const state = await reloaded
  expect(state.ok()).toBeTruthy()
  const data = await state.json()
  const sale = data.proposal.contracts.find(row => row.line_options?.some(line => line.cost_evidence === 'synthetic://browser-USD-cost'))
  expect(sale.line_options[0]).toMatchObject({ unit_cost: '9.3750', cost_currency: 'USD' })
  await writeFile(path.join(output, 'result.json'), JSON.stringify({ source: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
    browser: browser.version(), viewport: page.viewportSize(), devicePixelRatio: await page.evaluate(() => devicePixelRatio),
    saveStatus: response.status(), readback: sale.line_options[0], fixture }, null, 2))
})
