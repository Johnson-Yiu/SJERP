import { expect } from '@playwright/test'

const timeout = 25000
const files = ['synth-brief.txt', 'synth-follow-up.txt'].map(name => ({
  name, mimeType: 'text/plain', buffer: Buffer.from('Synthetic evidence only.'),
}))

export async function recordSalesJourneys({ page, settings, baseURL, fixture, customer, capture, results, saveIndex }) {
  const button = name => page.getByRole('button', { name, exact: true }).first()
  const visible = locator => expect(locator).toBeVisible({ timeout })
  const go = route => page.goto(new URL(route, baseURL).href, { waitUntil: 'domcontentloaded' })
  const orderRoute = '/orders?detail=' + fixture.order
  const quoteRoute = '/quotes?detail=' + fixture.quote
  const orderAPI = '/api/orders/' + fixture.order
  async function record(id, locator) {
    for (const zoom of [1, 1.25]) {
      await settings.goto('chrome://settings/appearance', { waitUntil: 'domcontentloaded' })
      await settings.locator('settings-appearance-page select').filter({
        has: settings.locator('option[value="1.25"]'),
      }).selectOption(String(zoom))
      for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
        if (process.env.SALES_STATE_WIDTH && Number(process.env.SALES_STATE_WIDTH) !== width) continue
        await page.setViewportSize({ width, height })
        if (width === 390) {
          await expect.poll(() => page.locator('.sidebar').evaluate(sidebar => sidebar.getBoundingClientRect().right), {
            timeout,
          }).toBeLessThanOrEqual(1)
        }
        if (locator) await locator.scrollIntoViewIfNeeded({ timeout })
        await capture(id, width, height, zoom)
        await saveIndex()
      }
    }
    await settings.locator('settings-appearance-page select').filter({
      has: settings.locator('option[value="1.25"]'),
    }).selectOption('1')
    await page.setViewportSize({ width: 1440, height: 900 })
  }

  async function scenario(id, run) {
    if (process.env.SALES_STATE_SCENARIOS && !process.env.SALES_STATE_SCENARIOS.split(',').includes(id)) return
    try {
      await run()
    } catch (error) {
      results.push({ id, outcome: 'incomplete', reason: String(error.message).split('\n')[0] })
      await saveIndex()
      console.log(id + ' incomplete: ' + String(error.message).split('\n')[0])
    }
  }

  async function mutate(id, predicate, action, expectedStatus) {
    const response = page.waitForResponse(r => predicate(new URL(r.url()).pathname)
      && ['POST', 'PUT', 'PATCH'].includes(r.request().method()), { timeout: 75000 })
    const [result] = await Promise.all([response, action()])
    const entry = { id, method: result.request().method(), path: new URL(result.url()).pathname, httpStatus: result.status() }
    if (!result.ok()) entry.error = await result.json().catch(() => null)
    results.push(entry)
    await saveIndex()
    if (expectedStatus) expect(result.status()).toBe(expectedStatus)
    else expect(result.ok()).toBe(true)
    return result
  }

  await scenario('C05-upload', async () => {
    await go('/follow-ups?search=SYNTH-SALES')
    const row = page.getByRole('row').filter({ hasText: 'SYNTH-SALES 附件与重开' })
    const edit = row.getByRole('button', { name: '编辑跟进记录' })
    await edit.click()
    const dialog = page.getByRole('dialog', { name: '编辑跟进记录' })
    await dialog.locator('input[type="file"]').setInputFiles(files)
    await visible(dialog.getByText(files[1].name))
    await record('C05-pending', dialog.getByText(files[1].name))
    await mutate('C05-save-http', p => p === '/api/follow-ups/' + fixture.followUp + '/', () => button('保存跟进').click())
    await expect(dialog).toHaveCount(0, { timeout })
    await edit.click()
    const attachment = dialog.locator('.follow-up-attachment-editor-item.saved').filter({ hasText: files[1].name })
    await visible(attachment)
    const href = await attachment.getByRole('link', { name: '查看' }).getAttribute('href')
    expect(href).toMatch(/^\/api\/media\//)
    const response = await page.request.get(new URL(href, baseURL).href)
    expect(response.status()).toBe(200)
    expect(await response.body()).toEqual(files[1].buffer)
    results.push({ id: 'C05-private-read', httpStatus: response.status(), bytes: files[1].buffer.length })
    await record('C05-reopened', attachment)
  })

  await scenario('O04-confirm', async () => {
    await go(orderRoute)
    await button('确认订单').click()
    await page.getByTestId('dialog-cancel').click()
    await visible(button('确认订单'))
    await button('确认订单').click()
    await record('O04-confirm-dialog', page.locator('.app-dialog'))
    await mutate('O04-confirm-http', p => p === orderAPI + '/confirm/', () => page.getByTestId('dialog-confirm').click())
    await visible(button('开始生产'))
    await record('O05-confirmed', button('开始生产'))
  })

  await scenario('O06-quantity', async () => {
    await go(orderRoute)
    await button('调整数量').click()
    const dialog = page.getByRole('dialog', { name: '调整订单数量' })
    await visible(dialog.getByText('数量没有变化。'))
    await record('O06-quantity-unchanged', dialog.getByText('数量没有变化。'))
    await dialog.getByRole('spinbutton', { name: /新的基础数量/ }).first().fill('12')
    await dialog.getByLabel('变更原因').fill('Synthetic quantity adjustment')
    await expect(button('预览影响')).toBeEnabled({ timeout })
    await mutate('O06-preview-http', p => p === orderAPI + '/quantity-adjustments/preview/', () => button('预览影响').click())
    await visible(button('确认调整'))
    await record('O06-quantity-preview', button('确认调整'))
  })

  await scenario('O07-shipment', async () => {
    await go(orderRoute)
    await visible(button('开始生产'))
    await mutate('O07-production-http', p => p === orderAPI + '/start-production/', () => button('开始生产').click())
    await go(orderRoute + '&tab=fulfillment')
    const rows = page.locator('.fulfillment-table tbody tr')
    await expect(rows).toHaveCount(4, { timeout })
    await record('O07-fulfillment', page.getByRole('region', { name: '履约状态摘要' }))
    await button('批量发货').click()
    const dialog = page.getByRole('dialog', { name: '确认发货' })
    const first = dialog.locator('.shipment-batch-line').first()
    const selection = dialog.getByRole('checkbox', { name: /^选择/ })
    for (const checkbox of (await selection.all()).slice(1)) await checkbox.uncheck()
    await first.getByRole('checkbox', { name: /^选择/ }).check()
    await first.getByRole('spinbutton', { name: /^发货数量/ }).fill('2')
    await record('O07-shipment-dialog', first.getByRole('spinbutton', { name: /^发货数量/ }))
    const submit = () => dialog.getByRole('button', { name: '确认发货' }).click()
    await mutate('O07-ship-default-location-http', p => p === orderAPI + '/ship/', submit, 400)
    const alert = dialog.getByRole('alert')
    await expect(alert).toContainText('所选仓库及批次库存不足', { timeout })
    await record('O07-location-validation', alert)
    await first.getByLabel('指定出库仓库和批次').check()
    await first.getByLabel('仓库', { exact: true }).fill('Synthetic warehouse')
    await mutate('O07-ship-http', p => p === orderAPI + '/ship/', submit, 201)
    const history = page.locator('.shipment-history-card').first()
    await visible(history)
    await record('O07-shipped', history)
    await history.getByRole('button', { name: '冲销', exact: true }).click()
    await page.getByLabel('冲销原因').fill('Synthetic shipment reversal')
    await record('O08-reversal-dialog', button('确认冲销'))
    await mutate('O08-reversal-http', p => /^\/api\/shipments\/\d+\/reverse\/$/.test(p), () => button('确认冲销').click())
    await go(orderRoute + '&tab=fulfillment')
    await visible(history.locator('.status').filter({ hasText: '已冲销' }))
    await record('O08-reversed', history)
  })

  await scenario('Q07-party', async () => {
    await go(quoteRoute)
    await button('主体更正').click()
    const panel = page.locator('#party-address')
    await visible(panel)
    await record('Q07-party-form', panel)
  })

  await scenario('C09-country', async () => {
    await go('/customers?detail=' + customer.id)
    await button('编辑客户').click()
    const search = page.getByPlaceholder('搜索名称、中文或代码后选择')
    await search.fill('SYNTH-NO-MATCH')
    await record('C09-country-search', search)
    await button('取消').click()
  })

  await scenario('C08-edit', async () => {
    await go('/customers?detail=' + customer.id)
    await button('编辑客户').click()
    const name = page.locator('.customer-editor .field').filter({ hasText: '客户名称' }).locator('input').first()
    const changed = customer.name + ' UPDATED'
    await name.fill(changed)
    await button('取消').click()
    const guard = page.getByText('未保存修改', { exact: true })
    await visible(guard)
    await record('C08-unsaved', guard)
    await page.getByTestId('dialog-cancel').click()
    await expect(name).toHaveValue(changed, { timeout })
    await mutate('C08-save-http', p => p === '/api/customers/' + customer.id + '/', () => button('保存客户').click())
    await visible(button('编辑客户'))
    await record('C08-saved', button('编辑客户'))
  })

  await scenario('C10-reminder', async () => {
    await go('/new-product-reminders?customer=' + customer.id)
    await button('记录新品需求').click()
    await page.getByLabel('所找产品').fill('Synthetic pendant light for a long commercial procurement brief')
    const saved = await mutate('C10-save-http', p => p === '/api/new-product-reminders/', () => button('保存需求').click(), 201)
    const { id } = await saved.json()
    await visible(button('作废'))
    await record('C10-saved', button('作废'))
    await button('作废').click()
    await expect(button('确认作废')).toBeDisabled({ timeout })
    await record('C10-void-reason-required', page.getByLabel('作废原因'))
    await page.getByLabel('作废原因').fill('Synthetic evidence reason')
    await mutate('C10-void-http', p => p === '/api/new-product-reminders/' + id + '/void/', () => button('确认作废').click())
    const reason = page.getByText('Synthetic evidence reason', { exact: false }).first()
    await visible(reason)
    await record('C10-voided', reason)
  })

  await scenario('Q05-return', async () => {
    await go(quoteRoute)
    await button('预览 PI').click()
    const preview = page.getByRole('dialog', { name: 'PI 预览' })
    await visible(preview)
    await preview.getByRole('button', { name: '关闭预览' }).click()
    await expect(preview).toHaveCount(0, { timeout })
    await expect(page).toHaveURL(new RegExp('[?&]detail=' + fixture.quote), { timeout })
    await record('Q05-return-to-quote', button('预览 PI'))
  })

  await scenario('Q04-revision', async () => {
    await go(quoteRoute)
    await button('创建修订版').click()
    const editor = page.getByRole('form', { name: '报价编辑器' })
    await expect(editor.locator('.quote-line-row')).toHaveCount(4, { timeout })
    await button('保存报价').click()
    const error = editor.getByText('请简要说明本次修改的内容。', { exact: true })
    await visible(error)
    await record('Q04-required-summary', error)
    await editor.getByPlaceholder('例如：调整数量、价格、交期或付款条款').fill('Synthetic revision for interface evidence')
    const response = await mutate('Q04-revise-http', p => p === '/api/quotes/' + fixture.quote + '/revise/', () => button('保存报价').click())
    const child = await response.json()
    expect(child.id).not.toBe(fixture.quote)
    await go('/quotes?detail=' + child.id)
    await visible(button('创建修订版'))
    await record('Q04-revision-saved', button('创建修订版'))
  })

  await scenario('O03-draft', async () => {
    await go(quoteRoute)
    await button('创建销售订单').click()
    await visible(button('保存销售订单草稿'))
    const response = await mutate('O03-draft-create-http', p => p === '/api/orders/', () => button('保存销售订单草稿').click(), 201)
    const order = await response.json()
    expect(order.status).toBe('draft')
    await go('/orders?detail=' + order.id)
    await button('编辑草稿').click()
    await page.getByLabel('交期天数').fill('12')
    await mutate('O03-draft-edit-http', p => p === '/api/orders/' + order.id + '/', () => button('保存销售订单草稿').click())
    await go('/orders?detail=' + order.id)
    await visible(button('编辑草稿'))
    await record('O03-draft-saved', button('编辑草稿'))
  })

  await scenario('C11-network', async () => {
    const match = url => url.pathname === '/api/customers/' && url.searchParams.has('search')
    await page.route(match, route => route.abort('failed'))
    try {
      await go('/customers')
      const error = page.getByText('数据加载失败', { exact: true })
      await visible(error)
      results.push({ id: 'C11-method', method: 'Playwright route.abort on customer list GET only' })
      await record('C11-network-failed', error)
      await page.unroute(match)
      await button('重新加载').click()
      await expect(page.getByRole('row').filter({ hasText: 'SYNTH-SALES' })).toHaveCount(1, { timeout })
      await record('C11-retry', page.getByRole('row').filter({ hasText: 'SYNTH-SALES' }))
    } finally {
      await page.unroute(match)
    }
  })
}
