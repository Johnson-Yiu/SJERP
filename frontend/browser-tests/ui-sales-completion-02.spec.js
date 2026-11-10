import { execFileSync } from 'node:child_process'
import { chromium, expect, test } from '@playwright/test'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'

const viewports = [[1366, 768], [1440, 900], [390, 844]]

test('sales fixes on real Chrome with native page zoom', async ({ baseURL }) => {
  test.setTimeout(2400000)
  const root = process.env.ISOLATED_TEST_ROOT
  const output = path.resolve(process.env.E1_R2_EVIDENCE_DIR)
  const extension = process.env.E1_R2_EXTRA || ''
  const widthFilter = process.env.E1_R2_WIDTH
  expect(['', '1', '2', '3', '4']).toContain(extension)
  if (widthFilter) expect(viewports.map(([width]) => String(width))).toContain(widthFilter)
  const core = !extension || extension === '1'
  await mkdir(output, { recursive: true })
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const seed = path.resolve('../docs/uat-evidence/ui-sales-completion-02/seed.py')
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], { encoding: 'utf8' }))
  const context = await chromium.launchPersistentContext(path.join(root, 'e1-r2-chrome'), {
    channel: 'chrome',
    viewport: { width: 1440, height: 900 },
  })
  context.setDefaultTimeout(75000)
  const results = []
  const failures = []
  try {
    const auth = JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8'))
    await context.addCookies(auth.cookies)
    await context.addInitScript(({ origins }) => {
      const current = origins.find(entry => entry.origin === location.origin)
      for (const item of current?.localStorage || []) localStorage.setItem(item.name, item.value)
    }, { origins: auth.origins })
    const settings = context.pages()[0]
    await settings.goto('chrome://settings/appearance', { waitUntil: 'commit' })
    const zoomControl = settings.locator('settings-appearance-page select').filter({
      has: settings.locator('option[value="1.25"]'),
    })
    await expect(zoomControl).toBeVisible({ timeout: 150000 })
    const page = await context.newPage()
    const cdp = await context.newCDPSession(page)
    const browser = (await cdp.send('Browser.getVersion')).product
    expect(browser).toMatch(/^Chrome\//)
    const save = () => writeFile(path.join(output, 'run.json'), JSON.stringify({ source, browser, results, failures }, null, 2))
    const go = route => page.goto(new URL(route, baseURL).href, { waitUntil: 'commit', timeout: 75000 })
    const button = name => page.getByRole('button', { name, exact: true }).first()

    async function collect(state, check) {
      for (const zoom of [1, 1.25]) {
        await zoomControl.selectOption(String(zoom))
        for (const [width, height] of viewports) {
          if (widthFilter && String(width) !== widthFilter) continue
          const key = state + '-' + width + '-' + zoom * 100
          try {
            await page.setViewportSize({ width, height })
            await expect.poll(() => page.evaluate(() => devicePixelRatio), { timeout: 15000 }).toBeCloseTo(zoom, 2)
            if (width === 390) await expect.poll(() => page.locator('.sidebar').evaluate(el => el.getBoundingClientRect().right)).toBeLessThanOrEqual(1)
            const metrics = await page.evaluate(() => {
              const root = document.documentElement
              const initial = window.scrollX
              window.scrollTo(100000, window.scrollY)
              const horizontalMovement = window.scrollX - initial
              window.scrollTo(initial, window.scrollY)
              const outside = [...document.querySelectorAll('body *')].filter(el => {
                const rect = el.getBoundingClientRect()
                return rect.width && rect.right > innerWidth + 4
              }).sort((a,b) => b.getBoundingClientRect().right - a.getBoundingClientRect().right).slice(0, 6)
                .map(el => ({ className: el.getAttribute('class'), right: el.getBoundingClientRect().right }))
              return { dpr: devicePixelRatio, clientWidth: root.clientWidth, scrollWidth: root.scrollWidth, horizontalMovement, outside }
            })
            const file = key + '.png'
            const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
            await writeFile(path.join(output, file), Buffer.from(data, 'base64'))
            const result = { key, width, height, zoom, file, ...metrics }
            results.push(result)
            await check(result)
          } catch (error) {
            failures.push({ key, error: String(error.message).slice(0, 900) })
          }
          await save()
        }
      }
      await zoomControl.selectOption('1')
      await page.setViewportSize({ width: 1440, height: 900 })
    }

    const noPageOverflow = result => {
      expect(result.scrollWidth).toBeLessThanOrEqual(result.clientWidth + 1)
      expect(result.horizontalMovement).toBe(0)
    }
    async function scenario(key, run) {
      try { await run() }
      catch (error) { failures.push({ key, error: String(error.message).slice(0, 900) }); await save() }
    }

    if (core) await scenario('quote-editor', async () => {
      await go('/quotes')
      await button('新建报价').click()
      const editor = page.getByRole('form', { name: '报价编辑器' })
      await expect(editor).toBeVisible()
      await collect('quote-new', noPageOverflow)
      await editor.locator('.sku-picker-options label').filter({ hasText: 'SYNTH-SALES-SKU-001' }).getByRole('checkbox').check()
      await expect(editor.locator('.quote-line-row')).toHaveCount(1)
      await collect('quote-selected', async result => {
        noPageOverflow(result)
        const table = editor.locator('.quote-line-items')
        const local = await table.evaluate(el => {
          const start = el.scrollLeft
          el.scrollLeft = el.scrollWidth
          const metrics = { width: el.clientWidth, scrollWidth: el.scrollWidth, moved: el.scrollLeft - start }
          el.scrollLeft = start
          return metrics
        })
        result.lineTable = local
        if (result.clientWidth <= 760) expect(local.moved).toBeGreaterThan(0)
      })
    })

    if (extension === '1') await scenario('quote-editor-recovery', async () => {
      const editor = page.getByRole('form', { name: '报价编辑器' })
      await editor.getByRole('button', { name: '保存报价', exact: true }).click()
      const requiredCustomer = editor.getByText('请选择客户。', { exact: true })
      await expect(requiredCustomer).toBeVisible()
      await collect('quote-selected-validation', async result => {
        noPageOverflow(result)
        await expect(requiredCustomer).toBeVisible()
      })

      const availability = '**/api/quotes/availability-preview/'
      let abort
      const release = new Promise(resolve => { abort = resolve })
      await page.route(availability, async route => { await release; await route.abort('failed') })
      try {
        await button('刷新库存').click()
        const loading = editor.getByText('正在读取库存参考…', { exact: true })
        await expect(loading).toBeVisible()
        await collect('quote-stock-loading', async result => {
          noPageOverflow(result)
          await expect(loading).toBeVisible()
        })
      } finally { abort() }
      const failure = editor.getByText('库存参考暂时无法读取，可继续报价。', { exact: true })
      await expect(failure).toBeVisible()
      await page.unroute(availability)
      await collect('quote-stock-failed', async result => {
        noPageOverflow(result)
        await expect(failure).toBeVisible()
      })
      const recovered = page.waitForResponse(r => r.url().endsWith('/availability-preview/'))
      await button('刷新库存').click()
      expect((await recovered).status()).toBe(200)
      await expect(editor.getByText('库存可覆盖', { exact: true })).toBeVisible()

      await button('生成预计装箱方案').click()
      await editor.getByRole('button', { name: /补充默认包装/ }).click()
      const packaging = page.locator('.packaging-config-modal')
      await expect(packaging.getByRole('heading', { name: '补充 SKU 默认包装' })).toBeVisible()
      await collect('quote-packaging-child', async result => {
        noPageOverflow(result)
        await packaging.getByRole('button', { name: '取消' }).click({ trial: true })
      })
      await packaging.getByRole('button', { name: '取消' }).click()
      await expect(packaging).toHaveCount(0)
      await expect(editor.locator('.quote-line-row')).toHaveCount(1)
      await expect(editor.getByRole('button', { name: /补充默认包装/ })).toBeVisible()

      await editor.getByRole('button', { name: '取消', exact: true }).click()
      await collect('quote-unsaved-close', async result => {
        noPageOverflow(result)
        await expect(button('继续编辑')).toBeVisible()
        await expect(button('放弃修改')).toBeVisible()
      })
      await button('继续编辑').click()
      await expect(editor.locator('.quote-line-row')).toHaveCount(1)
      await editor.getByRole('button', { name: '取消', exact: true }).click()
      await button('放弃修改').click()
      await expect(editor).toHaveCount(0)
    })

    if (core) await scenario('quote-revision', async () => {
      await go('/quotes?detail=' + fixture.quote)
      await button('创建修订版').click()
      await expect(page.locator('.quote-line-row')).toHaveCount(4)
      await collect('quote-revision', noPageOverflow)
    })

    if (core) await scenario('quote-preview', async () => {
      await go('/quotes?detail=' + fixture.quote)
      await button('预览 PI').click()
      const modal = page.getByRole('dialog', { name: 'PI 预览' })
      const img = modal.frameLocator('iframe[title="已保存 PI"]').locator('tbody img').first()
      await expect(modal).toBeVisible()
      await collect('quote-pi', async result => {
        await expect.poll(() => img.evaluate(node => node.naturalWidth)).toBe(48)
        await expect(img).toBeVisible()
        result.snapshot = await img.evaluate(node => ({
          imageOrigin: new URL(node.currentSrc).origin,
          frameOrigin: new URL(node.ownerDocument.baseURI).origin,
          width: node.naturalWidth,
        }))
        expect(result.snapshot.imageOrigin).toBe(result.snapshot.frameOrigin)
        noPageOverflow(result)
      })
      await modal.getByRole('button', { name: '关闭预览' }).click()
      await expect(button('预览 PI')).toBeVisible()
    })

    if (core) await scenario('order-badge', async () => {
      await go('/orders?detail=' + fixture.order)
      const badge = page.locator('.detail-identity .detail-badge')
      await expect(badge).toBeVisible()
      await collect('order-badge', async result => {
        const lines = await badge.evaluate(el => {
          const range = document.createRange()
          range.selectNodeContents(el)
          return new Set([...range.getClientRects()].map(rect => rect.top)).size
        })
        result.badgeLines = lines
        expect(lines).toBe(1)
        noPageOverflow(result)
      })
    })

    if (extension === '2') await scenario('order-terminal-states', async () => {
      await go('/orders?detail=' + fixture.order)
      const workbench = page.getByRole('dialog', { name: '订单工作台' })
      await workbench.getByRole('button', { name: '取消订单', exact: true }).click()
      const cancellation = page.locator('.trade-shipment-dialog').filter({ has: page.getByRole('heading', { name: '取消订单' }) })
      const confirm = cancellation.getByRole('button', { name: '确认取消', exact: true })
      await expect(confirm).toBeDisabled()
      await collect('order-cancel-required', async result => {
        noPageOverflow(result)
        await expect(confirm).toBeDisabled()
        await expect(cancellation.getByRole('button', { name: '返回' })).toBeVisible()
      })
      await cancellation.getByRole('button', { name: '返回' }).click()
      await expect(workbench.getByRole('button', { name: '编辑草稿' })).toBeVisible()
      await workbench.getByRole('button', { name: '取消订单', exact: true }).click()
      const reason = 'SYNTH-SALES 验收取消'
      await cancellation.getByLabel('取消原因').fill(reason)
      const cancelled = page.waitForResponse(r => r.url().endsWith('/cancel/') && r.request().method() === 'POST')
      await confirm.click()
      expect((await cancelled).status()).toBe(200)
      await expect(cancellation).toHaveCount(0)
      await go('/orders?detail=' + fixture.order)
      await expect(workbench.locator('.detail-badge')).toContainText('已取消')
      await expect(workbench.getByText(reason, { exact: false }).first()).toBeVisible()
      await collect('order-cancelled-read-only', async result => {
        noPageOverflow(result)
        await expect(workbench.getByRole('button', { name: '编辑草稿' })).toHaveCount(0)
        await expect(workbench.getByRole('button', { name: '取消订单' })).toHaveCount(0)
      })

      await go('/orders?detail=' + fixture.completedOrder)
      await expect(workbench.locator('.detail-badge')).toContainText('已完成')
      await collect('order-completed-read-only', async result => {
        noPageOverflow(result)
        await expect(workbench.getByRole('button', { name: '编辑草稿' })).toHaveCount(0)
        await expect(workbench.getByRole('button', { name: '取消订单' })).toHaveCount(0)
        await expect(workbench.getByRole('button', { name: '完成履约' })).toHaveCount(0)
      })
    })

    if (extension === '3') await scenario('order-procurement-draft', async () => {
      await go('/orders?detail=' + fixture.procurementOrder)
      const workbench = page.getByRole('dialog', { name: '订单工作台' })
      await workbench.getByRole('button', { name: '采购与发货', exact: true }).click()
      await button('生成采购草稿').click()
      const drawer = page.getByRole('dialog', { name: '采购草稿预览' })
      await expect(drawer.getByRole('heading', { name: '合成采购来源 · CNY' })).toBeVisible()
      const create = drawer.getByRole('button', { name: '创建 采购草稿' })
      const quantity = drawer.getByRole('row').filter({ hasText: 'SYNTH-PROCUREMENT' }).getByRole('spinbutton').first()
      await quantity.fill('16')
      await expect(drawer.getByText('本次采购数量必须介于 0 与当前可生成数量之间。')).toBeVisible()
      await expect(create).toBeDisabled()
      await quantity.fill('15')
      await collect('order-procurement-draft-preview', async result => {
        noPageOverflow(result)
        await expect(create).toBeEnabled()
      })

      const created = page.waitForResponse(r => r.url().endsWith('/generate-purchase-drafts/') && r.request().method() === 'POST')
      await create.click()
      const response = await created
      expect(response.status()).toBe(201)
      const { created_count, purchase_orders } = await response.json()
      expect(created_count).toBe(1)
      const [draft] = purchase_orders
      await expect(drawer).toHaveCount(0)
      await expect(workbench.getByRole('link', { name: draft.purchase_no })).toBeVisible()
      const stored = await page.request.get(`/api/purchase-orders/${draft.id}/`)
      expect(stored.status()).toBe(200)
      const record = await stored.json()
      expect(record.status).toBe('draft')
      expect(record.order).toBe(fixture.procurementOrder)
      expect(Number(record.items[0].quantity)).toBe(15)
      await go('/orders?detail=' + fixture.procurementOrder)
      await workbench.getByRole('button', { name: '采购与发货', exact: true }).click()
      await collect('order-procurement-draft-reopened', async result => {
        noPageOverflow(result)
        await expect(workbench.getByRole('link', { name: draft.purchase_no })).toBeVisible()
        await expect(button('生成采购草稿')).toBeDisabled()
      })
      results.push({ key: 'procurement-created-http', status: 201, purchase: draft.purchase_no, draftQuantity: 15 })
      await save()
    })

    if (extension === '4') await scenario('quote-trade-unit-and-packaging', async () => {
      await go('/quotes?create=1&customer=' + fixture.customer)
      const editor = page.getByRole('form', { name: '报价编辑器' })
      await editor.locator('.sku-picker-options label').filter({ hasText: 'SYNTH-SALES-SKU-001' }).getByRole('checkbox').check()
      const tradeUnit = editor.getByLabel('交易单位与包装规格')
      await tradeUnit.selectOption(String(fixture.tradeUnit))
      await editor.getByLabel('数量', { exact: true }).fill('2')
      await expect(editor.getByText(/^2(?:\.0+)? 箱 = 10 pcs$/)).toBeVisible()
      await button('生成预计装箱方案').click()
      await editor.getByRole('button', { name: /补充默认包装/ }).click()
      const packaging = page.locator('.packaging-config-modal')
      await packaging.locator('select').selectOption(String(fixture.carton))
      await packaging.getByRole('spinbutton').nth(0).fill('5')
      await packaging.getByRole('spinbutton').nth(1).fill('0.5')
      const savedPackaging = page.waitForResponse(r => r.url().endsWith('/packaging/') && r.request().method() === 'PUT')
      await packaging.getByRole('button', { name: '保存默认包装' }).click()
      expect((await savedPackaging).status()).toBe(200)
      await expect(packaging).toHaveCount(0)
      await expect(editor.locator('.packing-table-wrap tbody tr')).toHaveCount(2)
      await editor.locator('.packing-summary').scrollIntoViewIfNeeded()
      await collect('quote-packaging-saved-return', async result => {
        noPageOverflow(result)
        await expect(editor.getByText(/^2(?:\.0+)? 箱 = 10 pcs$/)).toBeVisible()
        await expect(editor.locator('.packing-table-wrap tbody tr')).toHaveCount(2)
      })

      const created = page.waitForResponse(r => r.url().endsWith('/api/quotes/') && r.request().method() === 'POST')
      await editor.getByRole('button', { name: '保存报价', exact: true }).click()
      const response = await created
      const saved = await response.json()
      expect(response.status(), JSON.stringify(saved)).toBe(201)
      expect(Number(saved.items[0].trade_unit)).toBe(fixture.tradeUnit)
      await go('/quotes?edit=' + saved.id)
      await expect(tradeUnit).toHaveValue(String(fixture.tradeUnit))
      await expect.poll(() => editor.getByLabel('数量', { exact: true }).evaluate(input => Number(input.value))).toBe(2)
      await expect(editor.getByText(/^2(?:\.0+)? 箱 = 10 pcs$/)).toBeVisible()
      await button('生成预计装箱方案').click()
      await expect(editor.locator('.packing-table-wrap tbody tr')).toHaveCount(2)
      results.push({ key: 'quote-trade-unit-reopened-http', quoteStatus: 201, packagingStatus: 200, cartons: 2, baseQuantity: 10 })
      await save()
    })

    if (core) await scenario('follow-up-attachment-retry', async () => {
      await go('/follow-ups?search=SYNTH-SALES')
      const row = page.getByRole('row').filter({ hasText: 'SYNTH-SALES 附件与重开' })
      await row.getByRole('button', { name: '编辑跟进记录' }).click()
      const dialog = page.getByRole('dialog', { name: '编辑跟进记录' })
      const bytes = Buffer.from('E1-R2 synthetic evidence')
      await dialog.locator('input[type=file]').setInputFiles({ name: 'e1-r2-retry.txt', mimeType: 'text/plain', buffer: bytes })
      const pattern = '**/api/follow-ups/' + fixture.followUp + '/attachments/'
      await page.route(pattern, route => route.request().method() === 'POST' ? route.abort('failed') : route.continue())
      try {
        await button('保存跟进').click()
        const error = dialog.getByText(/附件上传失败/).first()
        await expect(error).toBeVisible()
        await collect('follow-up-upload-error', async result => {
          noPageOverflow(result)
          await expect(error).toHaveText(/跟进记录已保存，附件上传失败/)
          await expect(button('取消')).toBeEnabled()
          await button('取消').click({ trial: true, timeout: 5000 })
          await button('保存跟进').click({ trial: true, timeout: 5000 })
          await expect(button('保存跟进')).toBeEnabled()
          expect(await dialog.locator('.toast').count()).toBe(0)
          expect(await page.locator('.toast.error').count()).toBe(0)
        })
      } finally { await page.unroute(pattern) }
      const upload = page.waitForResponse(r => r.url().endsWith('/attachments/') && r.request().method() === 'POST')
      await button('保存跟进').click()
      expect((await upload).status()).toBe(201)
      await expect(dialog).toHaveCount(0)
      await row.getByRole('button', { name: '编辑跟进记录' }).click()
      const attachment = dialog.locator('.follow-up-attachment-editor-item.saved')
      await expect(attachment).toHaveCount(1)
      const href = await attachment.getByRole('link', { name: '查看' }).getAttribute('href')
      const downloaded = await page.request.get(new URL(href, baseURL).href)
      expect(downloaded.status()).toBe(200)
      expect(await downloaded.body()).toEqual(bytes)
      results.push({ key: 'follow-up-reopened-http', status: 200, bytes: bytes.length, attachmentCount: 1 })
      await save()
    })

    expect(failures, JSON.stringify(failures, null, 2)).toEqual([])
    expect(results.some(result => result.file)).toBe(true)
  } finally {
    await context.close()
  }
})
