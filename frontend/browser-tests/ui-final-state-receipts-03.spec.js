import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect as playwrightExpect, test } from '@playwright/test'

const expect = playwrightExpect.configure({ timeout: 30000 })

test('receipts preserve both units and destinations and inventory movements enforce source-specific actions', async ({ baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)),
    'Requires a dedicated seeded database; run this spec through the isolated runner.')
  test.setTimeout(2400000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-purchase-receipt-combinations')
  await mkdir(output, { recursive: true })
  const seed = fileURLToPath(new URL('../../docs/uat-evidence/ui-final-state-closeout-03/seed.py', import.meta.url))
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.resolve('../backend'), encoding: 'utf8', env: { ...process.env, PRODUCT_OPS_RECEIPT_COMBINATIONS: '1' },
  }))
  const root = process.env.ISOLATED_TEST_ROOT
  const context = await chromium.launchPersistentContext(path.join(root, 'receipt-sources-chrome'), {
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
    page.setDefaultTimeout(90000)
    const cdp = await context.newCDPSession(page)
    browser = (await cdp.send('Browser.getVersion')).product
    expect(browser).toMatch(/^Chrome\//)
    await settings.goto('chrome://settings/appearance', { waitUntil: 'commit', timeout: 240000 })
    const zoomControl = settings.locator('settings-appearance-page select').filter({ has: settings.locator('option[value="1.25"]') })
    let zoom = 1.25
    await zoomControl.selectOption(String(zoom), { timeout: 180000 })
    const go = () => page.goto(new URL('/purchase-orders?detail=' + fixture.purchase, baseURL).href, { waitUntil: 'commit', timeout: 240000 })
    async function snap(id, extra = {}) {
      await expect.poll(() => page.evaluate(() => devicePixelRatio)).toBeCloseTo(zoom, 2)
      const dpr = await page.evaluate(() => devicePixelRatio)
      expect(dpr).toBeCloseTo(zoom, 2)
      const { width, height } = page.viewportSize()
      const png = id + '-' + width + '-' + zoom * 100 + '.png'
      const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
      await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
      states.push({ id, width, height, zoom, dpr, png, ...extra })
      await save()
    }
    await go()
    const workbench = page.getByRole('dialog', { name: '采购工作台' })
    const result = (fragment, method = 'POST') => page.waitForResponse(r => r.url().endsWith(fragment) && r.request().method() === method, { timeout: 75000 })
    const purchaseEndpoint = '/api/purchase-orders/' + fixture.purchase + '/'
    const beforePlace = await page.request.get(new URL(purchaseEndpoint, baseURL).href)
    const purchaseData = await beforePlace.json()
    if (Number(purchaseData.items[0].quantity) < 30) {
      await workbench.getByRole('button', { name: '编辑草稿', exact: true }).click()
      const draft = page.getByRole('dialog', { name: '编辑采购草稿' })
      const firstLine = draft.locator('.purchase-line').filter({ hasText: 'EVID-TRACK-LONG-SKU-3000K-BEAM24-BLACK-01' })
      await firstLine.getByPlaceholder('采购数量').fill('40')
      const draftSaved = result(purchaseEndpoint, 'PUT')
      await draft.getByRole('button', { name: '保存采购草稿', exact: true }).click()
      const amended = await draftSaved
      expect(amended.ok(), await amended.text()).toBeTruthy()
      await expect(draft).toHaveCount(0)
      await go()
    }
    await workbench.getByRole('button', { name: /确认.*下单/ }).first().click()
    const place = result('/place/')
    await page.getByTestId('dialog-confirm').click()
    const placed = await place
    expect(placed.ok()).toBeTruthy()
    expect(Number((await placed.json()).items[0].quantity)).toBeGreaterThanOrEqual(30)
    await expect(workbench.getByRole('button', { name: '编辑草稿', exact: true })).toHaveCount(0)
    await workbench.getByRole('button', { name: '分配采购成本 / 公共费用', exact: true }).click()
    const cost = page.locator('.cost-modal')
    const item = cost.locator('.cost-item').first()
    const addAllocation = item.getByRole('button', { name: '添加成本归属', exact: true })
    await expect(addAllocation).toBeVisible()
    const rows = item.locator('.cost-row')
    while (await rows.count()) await rows.first().getByRole('button', { name: '删除', exact: true }).click()
    for (const [order, quantity] of [['EVID-SO-001', '2'], ['EVID-SO-002', '3']]) {
      await addAllocation.click()
      const row = rows.last()
      await row.locator('select').nth(1).selectOption({ label: order })
      await row.locator('input[type=number]').fill(quantity)
    }
    await expect(rows).toHaveCount(2)
    const savedCost = result('/cost-allocation/')
    await cost.getByRole('button', { name: '保存成本分配', exact: true }).click()
    const allocated = await savedCost
    expect(allocated.ok(), await allocated.text()).toBeTruthy()
    const selectedOrders = (await allocated.json()).allocations.filter(row => row.target_type === 'order').map(row => row.order_no)
    expect(selectedOrders.sort()).toEqual(['EVID-SO-001', 'EVID-SO-002'])
    await expect(cost.getByText('已保存的成本分摊结果')).toBeVisible()
    await cost.getByText('已保存的成本分摊结果').scrollIntoViewIfNeeded()
    await snap('purchase-two-order-allocations')
    await go()
    await workbench.getByText('收货', { exact: true }).click()
    const form = page.locator('form.receipt-dialog')
    const submit = form.getByRole('button', { name: '确认入库', exact: true })
    const receiptTrigger = workbench.locator('.receipt-heading').first().getByRole('button', { name: '验货入库' })
    let receiptWrites = 0
    page.on('request', r => { if (r.url().endsWith('/receive/') && r.method() === 'POST') receiptWrites++ })

    async function prepare(warehouseType, warehouse, lot, quantity = '1', unitName) {
      await receiptTrigger.click()
      if (unitName) {
        const picker = form.getByRole('combobox', { name: '交易单位与包装规格' })
        const option = picker.locator('option').filter({ hasText: unitName })
        await picker.selectOption(await option.getAttribute('value'))
      }
      await form.getByLabel(/本次合格入库数量/).fill(quantity)
      await form.getByLabel('指定入库仓库和批次').check()
      await form.locator('label').filter({ hasText: '仓库类型' }).locator('select').selectOption(warehouseType)
      await form.getByLabel('仓库', { exact: true }).fill(warehouse)
      await form.getByLabel(/批次或货位/).fill(lot)
      await form.getByLabel(/已核对型号/).check()
    }
    async function verifyRejectedReceipt() {
      await prepare('自有仓', '合成收货甲仓', 'EVID-RECEIPT-MULTI-A')
      await page.route('**/receive/', route => route.fulfill({ status: 400, json: { detail: '合成校验错误，请重新核对' } }), { times: 1 })
      const failed = result('/receive/')
      await submit.click()
      expect((await failed).status()).toBe(400)
      await expect(form).toContainText('合成校验错误，请重新核对')
      await expect(form.getByLabel('仓库', { exact: true })).toHaveValue('合成收货甲仓')
      await snap('purchase-receipt-validation', { method: 'single controlled 400, no backend write' })
      await form.getByRole('button', { name: '取消', exact: true }).click()
      await expect(form).toHaveCount(0)
      await expect(receiptTrigger).toBeEnabled()
      await expect(receiptTrigger).toBeFocused()
      await snap('purchase-receipt-rejected-cancelled', { focusReturned: true })
    }
    await verifyRejectedReceipt()
    await receiptTrigger.press("Enter")
    await expect(form).toBeFocused()
    await page.keyboard.press("Escape")
    await expect(form).toHaveCount(0)
    await expect(receiptTrigger).toBeFocused()
    for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
      for (const scale of [1, 1.25]) {
        zoom = scale
        await zoomControl.selectOption(String(zoom))
        await page.setViewportSize({ width, height })
        await go()
        await workbench.getByText('收货', { exact: true }).click()
        if (width !== 390 || zoom !== 1.25) await verifyRejectedReceipt()
        await receiptTrigger.press('Enter')
        await expect(form).toBeFocused()
        await receiptTrigger.evaluate(element => element.remove())
        await expect(receiptTrigger).toHaveCount(0)
        await page.keyboard.press('Escape')
        await expect(form).toHaveCount(0)
        await expect(workbench).toBeFocused()
        await snap('purchase-receipt-detached-trigger', { method: 'controlled removal of the actual trigger, keyboard cancellation' })
      }
    }
    await go()
    await workbench.getByText('收货', { exact: true }).click()
    await expect(receiptTrigger).toBeVisible()
    const focusReturned = true
    await receiptTrigger.scrollIntoViewIfNeeded()
    await snap('purchase-receipt-validation-cancelled', { focusReturned })

    const rejectedReceiptWrites = receiptWrites
    expect(rejectedReceiptWrites).toBe(6)
    for (const [index, type, warehouse, lot, unitName] of [
      [1, '自有仓', '合成收货甲仓', 'EVID-RECEIPT-MULTI-A', '10 件／箱'],
      [2, '第三方仓', '合成收货乙仓', 'EVID-RECEIPT-MULTI-B', '20 件／大箱'],
    ]) {
      await prepare(type, warehouse, lot, '1', unitName)
      let release
      const pending = new Promise(resolve => { release = resolve })
      await page.route('**/receive/', async route => { await pending; await route.continue() }, { times: 1 })
      const saved = result('/receive/')
      try {
        await submit.evaluate(button => { button.click(); button.click() })
        await expect.poll(() => receiptWrites).toBe(rejectedReceiptWrites + index)
        await expect(form.getByRole('button', { name: /入库中|提交中|保存中/ })).toBeDisabled()
        await snap('purchase-receipt-pending-' + index, { method: 'temporarily held outgoing POST, then forwarded to real Django' })
      } finally {
        release()
      }
      const receipt = await saved
      expect(receipt.status(), await receipt.text()).toBe(201)
      await expect(form).toHaveCount(0)
      expect(receiptWrites).toBe(rejectedReceiptWrites + index)
      await expect(workbench.locator('.receipt-history-row')).toHaveCount(index)
    }
    const purchase = await page.request.get(new URL('/api/purchase-orders/' + fixture.purchase + '/', baseURL).href)
    const receiptRows = (await purchase.json()).items[0].receipts
    const destinations = await Promise.all(receiptRows.map(async receipt => {
      const reply = await page.request.get(new URL('/api/inventory-movements/' + receipt.inventory_movement + '/', baseURL).href)
      expect(reply.ok()).toBeTruthy()
      return reply.json()
    }))
    expect(destinations.map(movement => movement.warehouse).sort()).toEqual(['合成收货乙仓', '合成收货甲仓'].sort())
    expect(destinations.map(movement => movement.lot_reference).sort()).toEqual(['EVID-RECEIPT-MULTI-A', 'EVID-RECEIPT-MULTI-B'])
    expect(destinations.map(movement => Number(movement.quantity)).sort((a, b) => a - b)).toEqual([10, 20])
    expect(destinations.map(movement => Number(movement.trade_quantity))).toEqual([1, 1])
    await workbench.locator('.receipt-history-row').last().scrollIntoViewIfNeeded()
    await snap('purchase-receipt-two-destinations')

    await page.goto(new URL('/inventory-movements?search=' + encodeURIComponent('合成收货甲仓'), baseURL).href, { waitUntil: 'commit', timeout: 240000 })
    const automatic = page.locator('.workspace-pane[aria-hidden="false"] tbody tr').filter({ hasText: '合成收货甲仓' })
    await expect(automatic).toHaveCount(1)
    await expect(automatic).toContainText('系统自动')
    await expect(automatic.getByTitle('编辑', { exact: true })).toHaveCount(0)
    await expect(automatic.getByTitle('冲销', { exact: true })).toHaveCount(0)
    await automatic.getByTitle('查看详情', { exact: true }).click()
    const detail = page.getByRole('dialog', { name: '库存流水详情' })
    await expect(detail).toContainText('合成收货甲仓')
    await expect(detail.getByText('EVID-RECEIPT-MULTI-A', { exact: true })).toBeVisible()
    await expect(detail.getByRole('button', { name: '编辑主档' })).toHaveCount(0)
    for (const size of [{ width: 390, height: 844 }, { width: 1366, height: 768 }, { width: 1440, height: 900 }]) {
      await page.setViewportSize(size)
      for (const scale of [1, 1.25]) {
        zoom = scale
        await zoomControl.selectOption(String(zoom), { timeout: 180000 })
        await expect(detail.getByRole('button', { name: '关闭详情' })).toBeInViewport()
        await snap('inventory-automatic-receipt-readonly')
      }
    }
    await page.setViewportSize({ width: 390, height: 844 })
    const tabs = detail.locator('.detail-tabs button')
    await expect(tabs.first()).toBeVisible()
    for (const [index, tab] of (await tabs.all()).entries()) {
      const label = (await tab.innerText()).trim()
      await tab.click()
      await expect(tab).toHaveClass(/active/)
      await tab.scrollIntoViewIfNeeded()
      await snap('inventory-receipt-relation-tab-' + index, { label })
    }
    await detail.getByRole('button', { name: '关闭详情' }).click()
    await expect(detail).toHaveCount(0)

    await go()
    await workbench.getByText('收货', { exact: true }).click()
    await workbench.locator('.receipt-history-row').filter({ hasText: /到货 10/ }).getByRole('button', { name: '冲销', exact: true }).click()
    const reverse = page.getByRole('dialog', { name: '冲销采购入库' })
    await reverse.getByRole('textbox').fill('EVID 按采购来源冲销')
    const reversed = result('/reverse/')
    await reverse.getByRole('button', { name: '确认冲销' }).click()
    expect((await reversed).ok()).toBeTruthy()
    await expect(workbench.locator('.receipt-history-row').filter({ hasText: '已冲销' })).toHaveCount(1)
    await snap('purchase-reversal-source-only')
    await page.goto(new URL('/inventory-movements?search=' + encodeURIComponent('合成收货甲仓'), baseURL).href, { waitUntil: 'commit', timeout: 240000 })
    const ledger = page.locator('.workspace-pane[aria-hidden="false"] tbody tr')
    const cancelled = ledger.filter({ hasText: '已冲销' })
    const correction = ledger.filter({ hasText: '冲销生成' })
    await expect(cancelled).toHaveCount(1)
    await expect(correction).toHaveCount(1)
    for (const row of [cancelled, correction]) {
      await row.click()
      await expect(detail.getByText('EVID-RECEIPT-MULTI-A', { exact: true })).toBeVisible()
      await detail.getByRole('button', { name: '关闭详情' }).click()
      await expect(detail).toHaveCount(0)
      await expect(row.getByTitle('编辑', { exact: true })).toHaveCount(0)
      await expect(row.getByTitle('冲销', { exact: true })).toHaveCount(0)
    }
    await correction.scrollIntoViewIfNeeded()
    await snap('inventory-reversal-and-original-readonly')
  } catch (error) {
    failure = String(error.message)
    throw error
  } finally {
    await save()
    await context.close()
  }
})
