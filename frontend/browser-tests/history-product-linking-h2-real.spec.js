import { test, expect } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'

test.use({ channel: 'chrome', viewport: { width: 1440, height: 900 } })

test('H2 controlled candidate selection, specification recovery, audit, analysis and CSV', async ({ page, browser }, info) => {
  test.setTimeout(300_000)
  page.setDefaultTimeout(30_000)
  const output = process.env.H2_EVIDENCE_ROOT || info.outputPath('h2')
  await mkdir(output, { recursive: true })
  const capture = name => page.screenshot({ path: path.join(output, name + '.png') })
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [
    path.resolve('../docs/uat-evidence/history-product-linking-fixes-02/seed-browser.py'),
  ], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' }).trim().split('\n').at(-1))

  await page.goto('/history-takeover?application=' + fixture.candidate)
  await page.getByRole('button', { name: /H2-CANDIDATE/ }).click()
  const choose = page.getByRole('button', { name: '选用此候选' })
  await expect(choose).toBeVisible()
  await expect(page.getByText('正式灯具 B · B · 24W · pcs', { exact: true }).first()).toBeVisible()
  await choose.scrollIntoViewIfNeeded()
  await capture('candidate')
  await choose.click()
  await expect(page.getByLabel('选择现有对象')).toHaveValue('B')
  await expect(page.getByRole('button', { name: '保存关联并重新预检' })).toBeDisabled()
  await page.getByLabel('关联依据').fill('已与合成旧单的型号和规格核对')
  const saveMapping = page.waitForResponse(response => response.url().includes('/resolve-master/') && response.request().method() === 'POST')
  await page.getByRole('button', { name: '保存关联并重新预检' }).click()
  expect((await saveMapping).status()).toBe(200)
  await expect(page.getByText('已登记主档关联')).toBeVisible()

  await page.goto('/history-takeover?application=' + fixture.archived)
  await page.getByText('历史商品关联', { exact: true }).first().click()
  await page.getByRole('checkbox', { name: 'A1', exact: true }).check()
  await page.getByRole('button', { name: /处理所选商品/ }).click()
  const dialog = page.getByRole('dialog')
  const sku = dialog.getByLabel('正式 SKU', { exact: true })
  const target = sku.locator('option').filter({ hasText: /^B · 正式灯具 B/ })
  await expect(target).toHaveCount(1)
  await sku.selectOption(await target.getAttribute('value'))
  await expect(dialog.getByRole('button', { name: '生成预览' })).toBeEnabled()
  await dialog.getByRole('button', { name: '生成预览' }).click()
  await expect(dialog.getByRole('alert')).toHaveText(/关联未保存/)
  await capture('missing-specification-conflict')
  await dialog.getByLabel(/补核规格/).fill('24 W')
  await dialog.getByLabel(/原因/).fill('合成检验单 REF-H2-24')
  await dialog.getByRole('button', { name: '生成预览' }).click()
  await expect(dialog.getByRole('region', { name: '关联预览' })).toContainText('影响 1 条明细')
  await capture('verified-specification-preview')
  await dialog.getByRole('button', { name: '确认保存' }).click()
  await expect(dialog).not.toBeVisible()
  const audit = page.locator('.takeover-audit li').filter({ hasText: '合成检验单 REF-H2-24' })
  await expect(audit).toContainText('补核规格 24 W')
  await expect(audit).toContainText('正式灯具 B')
  await audit.scrollIntoViewIfNeeded()
  await capture('audit-detail')

  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: '导出 CSV' }).click()
  const csv = await download
  expect(csv.suggestedFilename()).toBe('history-products.csv')
  const csvPath = path.join(output, csv.suggestedFilename())
  await csv.saveAs(csvPath)
  const exported = await readFile(csvPath, 'utf8')
  expect(exported).toContain('历史原文明细')
  expect(exported).toMatch(/A1,,旧分类,2(?:\.0+)?,pcs,50(?:\.0+)?,CNY,已关联,B/)

  await page.goto('/historical-orders')
  const analysis = page.locator('.analysis-card')
  const grouping = analysis.getByLabel('商品口径')
  await expect(analysis.getByRole('heading', { name: '历史原文' })).toBeVisible()
  await grouping.selectOption('linked')
  await expect(analysis.getByRole('heading', { name: '按关联 SKU 归集' })).toBeVisible()
  await capture('linked-analysis')

  await page.route('**/api/reports/historical/**', route => route.fulfill({ status: 503, json: { detail: '合成网络失败，等待重试' } }), { times: 1 })
  await grouping.selectOption('original')
  await expect(analysis.getByRole('alert')).toHaveText('服务器暂时不可用，请稍后重试。')
  await analysis.getByRole('button', { name: '刷新分析' }).click()
  await expect(analysis.getByRole('heading', { name: '历史原文' })).toBeVisible()
  await capture('original-analysis-recovered')
  await writeFile(path.join(output, 'chrome-checks.json'), JSON.stringify({
    chrome: browser.version(), viewport: page.viewportSize(), nativeZoom: '100%',
    sourceSha: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
    backend: 'isolated SQLite and media root; only 503 analysis recovery response injected',
  }, null, 2))
})
