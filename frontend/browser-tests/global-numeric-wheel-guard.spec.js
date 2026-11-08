import { test, expect } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'

test.use({ channel: 'chrome' })

test('Chrome native wheel scrolls the owning container without stepping numeric controls', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/')
  await page.evaluate(() => {
    document.body.innerHTML = `
      <style>
        body { margin: 0; min-height: 2400px; font: 16px Arial, sans-serif; }
        #fixture { display: grid; gap: 14px; padding: 28px; }
        .control { width: 220px; height: 34px; }
        .modal { position: fixed; top: 240px; right: 32px; width: 420px; height: 310px; overflow: auto; padding: 20px; background: #eef5f0; border: 1px solid #8ca99b; }
        .nested { height: 120px; overflow: auto; border: 1px solid #567568; }
        .nested-content { height: 500px; padding-top: 8px; }
        #nested-number { position: sticky; top: 0; z-index: 1; }
        .modal-fill { height: 500px; }
      </style>
      <main id="fixture">
        <label>Positive <input id="positive" class="control" type="number" value="12" step="1"></label>
        <label>Negative <input id="negative" class="control" type="number" value="-12.5" step="0.1"></label>
        <label>Decimal <input id="decimal" class="control" type="number" value="1.25" step="0.01"></label>
        <label>Empty <input id="empty" class="control" type="number" value="" step="any"></label>
        <label>Read only <input id="readonly" class="control" type="number" value="4.5" readonly></label>
        <label>Disabled <input id="disabled" class="control" type="number" value="-3" disabled></label>
        <label>Text <input id="text" class="control" type="text" value="ordinary"></label>
        <label>Notes <textarea id="textarea" class="control">ordinary notes</textarea></label>
        <div id="custom-spin" role="spinbutton" tabindex="0" aria-valuenow="9">9</div>
        <div id="dynamic-rows"><table><tbody></tbody></table></div>
        <button id="add-row" type="button">Add row</button>
        <button id="open-tab" type="button">Open internal tab</button>
        <button id="step-up" type="button">Step up</button>
        <button id="save" type="button">Save</button>
        <div id="tab-content"></div>
      </main>
      <section class="modal" role="dialog" aria-label="Scroll test dialog">
        <label>Dialog amount <input id="modal-number" class="control" type="number" value="6.25" step="0.01"></label>
        <div class="nested"><div class="nested-content"><label>Nested quantity <input id="nested-number" class="control" type="number" value="8.5" step="0.1"></label><div style="height:420px"></div></div></div>
        <div class="modal-fill"></div>
      </section>`

    window.__wheelState = { inputEvents: 0, changeEvents: 0, saves: 0, model: {} }
    document.addEventListener('input', event => {
      window.__wheelState.inputEvents += 1
      if (event.target.id) window.__wheelState.model[event.target.id] = event.target.value
    })
    document.addEventListener('change', () => { window.__wheelState.changeEvents += 1 })
    document.querySelector('#custom-spin').addEventListener('wheel', event => {
      event.currentTarget.textContent = String(Number(event.currentTarget.textContent) + Math.sign(event.deltaY))
    })
    document.querySelector('#add-row').addEventListener('click', () => {
      const input = document.createElement('input')
      input.id = 'dynamic-number'
      input.className = 'control'
      input.type = 'number'
      input.value = '17.75'
      input.step = '0.01'
      const cell = document.createElement('td')
      const row = document.createElement('tr')
      cell.append(input)
      row.append(cell)
      document.querySelector('#dynamic-rows tbody').append(row)
    })
    document.querySelector('#open-tab').addEventListener('click', () => {
      history.pushState({ tab: 'second' }, '', '/quotes?tab=second')
      document.querySelector('#tab-content').innerHTML = '<input id="tab-number" class="control" type="number" value="21.5" step="0.01">'
    })
    document.querySelector('#step-up').addEventListener('click', () => {
      const input = document.querySelector('#positive')
      input.stepUp()
      input.dispatchEvent(new Event('input', { bubbles: true }))
    })
    document.querySelector('#save').addEventListener('click', () => { window.__wheelState.saves += 1 })
  })

  if (process.env.GLOBAL_NUMERIC_WHEEL_EVIDENCE_DIR) {
    await fs.mkdir(process.env.GLOBAL_NUMERIC_WHEEL_EVIDENCE_DIR, { recursive: true })
    await page.screenshot({ path: path.join(process.env.GLOBAL_NUMERIC_WHEEL_EVIDENCE_DIR, 'chrome-page-and-dialog-wheel.png'), fullPage: false })
  }

  const getSnapshot = () => page.evaluate(() => ({
    values: Object.fromEntries(['positive', 'negative', 'decimal', 'empty', 'readonly', 'disabled', 'modal-number', 'nested-number', 'text', 'textarea', 'dynamic-number', 'tab-number', 'custom-spin'].map(id => [id, document.getElementById(id)?.value ?? document.getElementById(id)?.textContent ?? null])),
    pageTop: window.scrollY,
    modalTop: document.querySelector('.modal').scrollTop,
    nestedTop: document.querySelector('.nested').scrollTop,
    outerTop: document.querySelector('.modal').scrollTop,
    active: document.activeElement?.id,
    inputEvents: window.__wheelState.inputEvents,
    changeEvents: window.__wheelState.changeEvents,
    saves: window.__wheelState.saves,
    model: { ...window.__wheelState.model },
  }))

  const wheelOn = async (id, { focus = false, delta = 120, expectedScroll = 'page', direction = 1 } = {}) => {
    const control = page.locator(`#${id}`)
    await control.scrollIntoViewIfNeeded()
    if (focus) await control.evaluate(element => element.focus({ preventScroll: true }))
    else await page.locator('#text').evaluate(element => element.focus())
    const box = await control.boundingBox()
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
    const before = await getSnapshot()
    await page.mouse.wheel(0, delta)
    await page.waitForTimeout(80)
    const after = await getSnapshot()

    expect(after.values[id], `${id} value`).toBe(before.values[id])
    expect(after.inputEvents).toBe(before.inputEvents)
    expect(after.changeEvents).toBe(before.changeEvents)
    expect(after.saves).toBe(before.saves)
    expect(after.model).toEqual(before.model)
    if (focus) expect(after.active).toBe(id)
    if (expectedScroll === 'page') expect((after.pageTop - before.pageTop) * direction).toBeGreaterThan(0)
    if (expectedScroll === 'modal') expect((after.modalTop - before.modalTop) * direction).toBeGreaterThan(0)
    if (expectedScroll === 'nested') expect((after.nestedTop - before.nestedTop) * direction).toBeGreaterThan(0)
    if (expectedScroll === 'outer') expect((after.outerTop - before.outerTop) * direction).toBeGreaterThan(0)
  }

  await wheelOn('positive', { focus: true })
  await page.locator('#positive').evaluate(element => element.focus({ preventScroll: true }))
  await page.locator('#text').evaluate(element => element.scrollIntoView({ block: 'center' }))
  const focusedElsewhereBefore = await getSnapshot()
  const textBox = await page.locator('#text').boundingBox()
  await page.mouse.move(textBox.x + textBox.width / 2, textBox.y + textBox.height / 2)
  await page.mouse.wheel(0, 120)
  await page.waitForTimeout(80)
  const focusedElsewhereAfter = await getSnapshot()
  expect(focusedElsewhereAfter.values.positive).toBe(focusedElsewhereBefore.values.positive)
  expect(focusedElsewhereAfter.active).toBe('positive')
  expect(focusedElsewhereAfter.pageTop).toBeGreaterThan(focusedElsewhereBefore.pageTop)
  expect(focusedElsewhereAfter.inputEvents).toBe(focusedElsewhereBefore.inputEvents)
  expect(focusedElsewhereAfter.changeEvents).toBe(focusedElsewhereBefore.changeEvents)
  await wheelOn('negative')
  await wheelOn('decimal', { focus: true })
  await wheelOn('empty')
  await wheelOn('readonly')
  await wheelOn('disabled')
  await wheelOn('custom-spin')
  expect((await getSnapshot()).values['custom-spin']).toBe('9')
  await wheelOn('modal-number', { focus: true, expectedScroll: 'modal' })

  await page.evaluate(() => {
    const nested = document.querySelector('.nested')
    nested.scrollTop = 0
  })
  await wheelOn('nested-number', { focus: true, expectedScroll: 'nested' })
  await wheelOn('nested-number', { focus: true, delta: -120, expectedScroll: 'nested', direction: -1 })
  await page.evaluate(() => { document.querySelector('.nested').scrollTop = 900 })
  await wheelOn('nested-number', { expectedScroll: 'outer' })

  await page.getByRole('button', { name: 'Add row' }).click()
  await wheelOn('dynamic-number')
  await page.getByRole('button', { name: 'Open internal tab' }).click()
  await wheelOn('tab-number')

  const beforePlainScroll = await getSnapshot()
  await wheelOn('text', { expectedScroll: 'page' })
  await wheelOn('textarea', { expectedScroll: 'page' })
  const afterPlainScroll = await getSnapshot()
  expect(afterPlainScroll.values.text).toBe(beforePlainScroll.values.text)
  expect(afterPlainScroll.values.textarea).toBe(beforePlainScroll.values.textarea)

  const positive = page.locator('#positive')
  await positive.evaluate(element => element.focus({ preventScroll: true }))
  await page.keyboard.press('Tab')
  await expect(page.locator('#negative')).toBeFocused()
  await positive.focus({ preventScroll: true })
  await page.keyboard.press('ArrowUp')
  await expect(positive).toHaveValue('13')
  await page.getByRole('button', { name: 'Step up' }).click()
  await expect(positive).toHaveValue('14')
  await positive.fill('15.5')
  await expect(positive).toHaveValue('15.5')
  await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
  await page.evaluate(() => navigator.clipboard.writeText('16.75'))
  await positive.focus({ preventScroll: true })
  await page.keyboard.press('Control+A')
  await page.keyboard.press('Control+V')
  await expect(positive).toHaveValue('16.75')
})

test('isolated ERP finance, quote/order, SKU/packaging and inventory forms keep their values on native wheel input', async ({ page }) => {
  test.skip(process.env.ISOLATED_CODEX_TEST_SUPERADMIN !== '1', 'Run through the isolated codex browser profile for real ERP pages.')

  await page.setViewportSize({ width: 1600, height: 820 })
  const evidenceDir = process.env.GLOBAL_NUMERIC_WHEEL_EVIDENCE_DIR
  if (evidenceDir) await fs.mkdir(evidenceDir, { recursive: true })
  const mutations = []
  page.on('request', request => {
    const url = new URL(request.url())
    if (url.pathname.startsWith('/api/') && !['GET', 'HEAD', 'OPTIONS'].includes(request.method())) {
      mutations.push(`${request.method()} ${url.pathname}`)
    }
  })
  await page.addInitScript(() => {
    window.__numericWheelEvents = { input: 0, change: 0 }
    document.addEventListener('input', event => {
      if (event.target instanceof HTMLInputElement && event.target.type === 'number') window.__numericWheelEvents.input += 1
    }, true)
    document.addEventListener('change', event => {
      if (event.target instanceof HTMLInputElement && event.target.type === 'number') window.__numericWheelEvents.change += 1
    }, true)
  })

  const verifyWheel = async (field, value, screenshotName) => {
    await expect(field).toBeVisible()
    await field.scrollIntoViewIfNeeded()
    const readonly = await field.evaluate(element => element.readOnly || element.disabled)
    if (!readonly && value !== undefined) await field.fill(value)
    const beforeValue = await field.inputValue()
    const beforeEvents = await page.evaluate(() => ({ ...window.__numericWheelEvents }))
    const beforePreview = await page.locator('.totals, .conversion-preview, .movement-lines-head').allTextContents()
    await field.focus()
    const readScrollables = () => field.evaluate(element => {
      const scrollables = []
      for (let node = element; node && node !== document.body; node = node.parentElement) {
        const style = getComputedStyle(node)
        const max = node.scrollHeight - node.clientHeight
        if (['auto', 'scroll', 'overlay'].includes(style.overflowY) && max > 1) scrollables.push([node.scrollTop, max])
      }
      const root = document.scrollingElement
      const rootMax = root?.scrollHeight - root?.clientHeight
      if (root && getComputedStyle(document.body).overflowY !== 'hidden' && rootMax > 1) scrollables.push([root.scrollTop, rootMax])
      return scrollables
    })
    const beforeScroll = await readScrollables()
    const direction = beforeScroll.some(([top, max]) => top < max - 1) ? 1 : -1
    const box = await field.boundingBox()
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
    await page.mouse.wheel(0, 120 * direction)
    await page.waitForTimeout(80)
    await expect(field).toHaveValue(beforeValue)
    expect(await page.evaluate(() => window.__numericWheelEvents)).toEqual(beforeEvents)
    expect(await page.locator('.totals, .conversion-preview, .movement-lines-head').allTextContents()).toEqual(beforePreview)
    const afterScroll = await readScrollables()
    const canMove = beforeScroll.some(([top, max]) => direction > 0 ? top < max - 1 : top > 1)
    if (canMove) expect(afterScroll.some(([top], index) => top !== beforeScroll[index]?.[0])).toBe(true)
    if (evidenceDir && screenshotName) await page.screenshot({ path: path.join(evidenceDir, screenshotName), fullPage: false })
  }

  await page.goto('/transactions')
  await page.getByRole('button', { name: '新增记账', exact: true }).click()
  const finance = page.getByRole('dialog', { name: '新增记账' })
  const financeAmount = finance.locator('input[type="number"]').first()
  await verifyWheel(financeAmount, '12.34', 'real-finance-form.png')

  await page.goto('/quotes?create=1')
  const quote = page.locator('.quote-editor-modal')
  const quoteRate = quote.getByLabel('对人民币汇率')
  await verifyWheel(quoteRate, '7.123456', 'real-quote-form.png')

  await page.goto('/orders?create=1')
  const order = page.locator('.modal-backdrop .modal.wide')
  const orderRate = order.getByLabel('对人民币汇率')
  await verifyWheel(orderRate, '7.654321', 'real-order-form.png')

  await page.goto('/skus?create=1')
  const skuDialog = page.getByRole('dialog', { name: '新建 SKU' })
  await skuDialog.locator('.sku-basics select').first().selectOption({ label: 'Wheel Guard Test Product' })
  await skuDialog.getByRole('button', { name: /包装与发货/ }).click()
  const skuPackagingInput = skuDialog.locator('[data-sku-step="4"] input[type="number"]').first()
  await verifyWheel(skuPackagingInput, '8.250', 'real-sku-packaging-form.png')

  await page.goto('/sku-packaging')
  await page.getByRole('button', { name: '新建模板' }).click()
  const packaging = page.getByRole('dialog', { name: '新建包装模板' })
  await verifyWheel(packaging.getByLabel('长 (cm)'), '123.4', 'real-packaging-form.png')

  await page.goto('/inventory-movements')
  await page.getByRole('button', { name: '新建库存调整' }).click()
  const inventory = page.getByRole('dialog', { name: '新建手工库存流水' })
  const skuChoice = inventory.locator('.sku-picker-options label').filter({ hasText: 'WG-TEST-SKU-01' })
  await expect(skuChoice).toBeVisible()
  const skuCheckbox = skuChoice.locator('input[type="checkbox"]')
  await skuCheckbox.dispatchEvent('click')
  await expect(skuCheckbox).toBeChecked()
  await verifyWheel(inventory.locator('.movement-line-wrap input[type="number"]').first(), '3.25', 'real-inventory-form.png')

  expect(mutations).toEqual([])
})
