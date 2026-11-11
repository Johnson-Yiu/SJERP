import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'

test('supplier binding edit persists, preferred source switches and the purchase editor fills the selected price', async ({ baseURL }) => {
  test.setTimeout(2400000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-supplier-purchase-trade')
  await mkdir(output, { recursive: true })
  const seed = fileURLToPath(new URL('../../docs/uat-evidence/ui-product-operations-completion-02/seed.py', import.meta.url))
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.resolve('../backend'), encoding: 'utf8',
  }))
  const root = process.env.ISOLATED_TEST_ROOT
  const context = await chromium.launchPersistentContext(path.join(root, 'supplier-purchase-chrome'), {
    channel: 'chrome', viewport: { width: 390, height: 844 },
  })
  const states = []
  let browser
  let failure
  const save = () => writeFile(path.join(output, 'run.json'), JSON.stringify({ source, browser, states, failure }, null, 2) + '\n')
  try {
    const auth = JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8'))
    await context.addCookies(auth.cookies)
    const settings = context.pages()[0]
    const page = await context.newPage()
    page.setDefaultTimeout(45000)
    const cdp = await context.newCDPSession(page)
    browser = (await cdp.send('Browser.getVersion')).product
    expect(browser).toMatch(/^Chrome\//)
    await settings.goto('chrome://settings/appearance', { waitUntil: 'domcontentloaded', timeout: 100000 })
    await settings.locator('settings-appearance-page select').filter({ has: settings.locator('option[value="1.25"]') }).selectOption('1.25')
    const go = () => page.goto(new URL('/skus', baseURL).href, { waitUntil: 'domcontentloaded', timeout: 100000 })
    async function snap(id, extra = {}) {
      const dpr = await page.evaluate(() => devicePixelRatio)
      expect(dpr).toBeCloseTo(1.25, 2)
      const png = id + '-390-125.png'
      const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
      await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
      states.push({ id, width: 390, height: 844, zoom: 1.25, dpr, png, ...extra })
      await save()
    }
    await go()
    const row = page.getByRole('row').filter({ hasText: 'EVID-TRACK-LONG-SKU-3000K-BEAM24-BLACK-01' })
    await row.getByRole('button', { name: '编辑', exact: true }).click()
    const edit = page.getByRole('dialog', { name: '编辑 SKU' })
    const oldSource = edit.getByRole('row').filter({ hasText: 'EVID-SUPPLY-01' })
    await oldSource.getByRole('button', { name: '设为首选', exact: true }).click()
    await expect(oldSource).toContainText('首选')
    await oldSource.getByRole('button', { name: '编辑', exact: true }).click()
    const form = page.getByRole('dialog', { name: '编辑供应商来源' })
    await form.getByLabel('供应商型号').fill('EVID-MODEL-UPDATED')
    await form.getByLabel('参考采购价').fill('7.25')
    const [patch] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/supplier-skus/') && r.request().method() === 'PATCH', { timeout: 75000 }),
      form.getByRole('button', { name: '保存来源' }).click(),
    ])
    expect(patch.ok(), await patch.text()).toBeTruthy()
    await expect(form).toHaveCount(0)
    await expect(oldSource).toContainText('EVID-MODEL-UPDATED')
    const updated = await patch.json()
    await edit.getByRole('button', { name: '添加供应商来源' }).click()
    const newForm = page.getByRole('dialog', { name: '添加供应商来源' })
    await newForm.getByLabel('供应商', { exact: false }).filter({ has: page.locator('option') }).first().selectOption(String(fixture.supplier))
    await newForm.getByLabel('供应商 SKU Code').fill('EVID-SUPPLY-ALT')
    await newForm.getByLabel('参考采购价').fill('8.50')
    await newForm.getByRole('button', { name: '保存来源' }).click()
    await expect(newForm).toHaveCount(0)
    const alternate = edit.getByRole('row').filter({ hasText: 'EVID-SUPPLY-ALT' })
    const [switched] = await Promise.all([
      page.waitForResponse(r => r.url().endsWith('/set-preferred/') && r.request().method() === 'POST', { timeout: 75000 }),
      alternate.getByRole('button', { name: '设为首选' }).click(),
    ])
    expect(switched.ok()).toBeTruthy()
    const former = await page.request.get(new URL('/api/supplier-skus/' + updated.id + '/', baseURL).href)
    expect(await former.json()).toMatchObject({ is_preferred: false, supplier_model: 'EVID-MODEL-UPDATED' })
    await expect(alternate.getByRole('button', { name: '设为首选' })).toHaveCount(0)
    await alternate.scrollIntoViewIfNeeded()
    await snap('supplier-preferred-switched')
    await edit.getByRole('button', { name: '关闭 SKU 窗口' }).click()
    await page.goto(new URL('/purchase-orders', baseURL).href, { waitUntil: 'domcontentloaded', timeout: 100000 })
    await page.getByRole('button', { name: /新建采购单/ }).click()
    const purchase = page.getByRole('dialog', { name: '新建采购单' })
    await purchase.getByRole('combobox', { name: '供应商', exact: true }).selectOption(String(fixture.supplier))
    await purchase.locator('.sku-picker-options label').filter({ hasText: 'EVID-TRACK-LONG-SKU-3000K-BEAM24-BLACK-01' }).locator('input').check()
    const purchaseSource = purchase.getByRole('combobox', { name: '供应商供货档案', exact: true })
    await expect(purchaseSource).toBeEnabled()
    const option = purchaseSource.locator('option').filter({ hasText: 'EVID-SUPPLY-ALT' })
    await expect(option).toHaveCount(1)
    const selectedId = await option.getAttribute('value')
    expect(await purchaseSource.inputValue()).toBe('')
    await purchaseSource.selectOption(selectedId)
    const price = purchase.getByPlaceholder('采购单价')
    await expect(purchase).toContainText('参考价未自动带入')
    await expect(price).toHaveValue('')
    await snap('purchase-source-currency-mismatch')
    await purchase.getByLabel('采购币种').selectOption('USD')
    await purchase.getByPlaceholder('1 单位外币兑换人民币金额').fill('7.2')
    await purchase.locator('.trade-unit-picker select').selectOption('')
    await purchaseSource.selectOption(selectedId)
    await expect.poll(async () => Number(await price.inputValue())).toBe(8.5)
    const trade = purchase.getByRole('combobox', { name: '交易单位与包装规格' })
    const tradeOption = trade.locator('option').filter({ hasText: '10 件／箱' })
    const tradeId = await tradeOption.getAttribute('value')
    await trade.selectOption(tradeId)
    await expect.poll(async () => Number(await price.inputValue())).toBe(85)
    await purchase.getByPlaceholder('采购数量').fill('2')
    await price.scrollIntoViewIfNeeded()
    await snap('purchase-source-price-filled')
    const [post] = await Promise.all([
      page.waitForResponse(r => r.url().endsWith('/api/purchase-orders/') && r.request().method() === 'POST', { timeout: 75000 }),
      purchase.getByRole('button', { name: /创建采购单|保存采购草稿/ }).click(),
    ])
    expect(post.status(), await post.text()).toBe(201)
    const purchaseId = (await post.json()).id
    const reopened = await page.request.get(new URL('/api/purchase-orders/' + purchaseId + '/', baseURL).href)
    expect(reopened.ok()).toBeTruthy()
    const lines = (await reopened.json()).items
    expect(lines).toHaveLength(1)
    expect(Number(lines[0].supplier_sku)).toBe(Number(selectedId))
    expect(Number(lines[0].unit_price)).toBe(8.5)
    expect(Number(lines[0].trade_unit_price)).toBe(85)
    expect(Number(lines[0].quantity)).toBe(20)
    expect(Number(lines[0].trade_quantity)).toBe(2)
    await expect(purchase).toHaveCount(0)
    await snap('purchase-source-persisted', { httpStatus: post.status() })
    const snapshot = lines[0].trade_snapshot
    expect(Number(snapshot.factor)).toBe(10)
    expect(snapshot.name).toBe('10 件／箱')
    await page.goto(new URL('/sku-trade-units?sku=' + fixture.sku, baseURL).href, { waitUntil: 'domcontentloaded', timeout: 100000 })
    const tradeRow = page.locator('.units-layout tbody tr').filter({ hasText: '10 件／箱' })
    await tradeRow.getByRole('button', { name: '停用', exact: true }).click()
    await snap('trade-stop-confirmation')
    const [stop] = await Promise.all([
      page.waitForResponse(r => r.url().endsWith('/api/sku-trade-units/' + tradeId + '/') && r.request().method() === 'PATCH', { timeout: 75000 }),
      page.getByRole('button', { name: '确认停用', exact: true }).click(),
    ])
    expect(stop.ok(), await stop.text()).toBeTruthy()
    expect((await stop.json()).active).toBe(false)
    const afterStop = await page.request.get(new URL('/api/purchase-orders/' + purchaseId + '/', baseURL).href)
    expect((await afterStop.json()).items[0].trade_snapshot).toEqual(snapshot)
    await page.goto(new URL('/purchase-orders?detail=' + purchaseId, baseURL).href, { waitUntil: 'domcontentloaded', timeout: 100000 })
    await page.getByRole('button', { name: '编辑草稿', exact: true }).click()
    const savedTrade = page.getByRole('dialog', { name: '编辑采购草稿' }).getByRole('combobox', { name: '交易单位与包装规格' })
    await expect(savedTrade).toHaveValue(tradeId)
    await expect(savedTrade.locator('option:checked')).toContainText(/历史/)
    await savedTrade.scrollIntoViewIfNeeded()
    await snap('trade-stopped-purchase-snapshot-reopened')
  } catch (error) {
    failure = String(error.message)
    throw error
  } finally {
    await save()
    await context.close()
  }
})
