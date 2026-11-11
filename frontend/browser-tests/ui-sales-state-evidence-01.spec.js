import { execFileSync } from 'node:child_process'
import { chromium, expect, test } from '@playwright/test'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { recordSalesJourneys } from './ui-sales-state-evidence-01.journeys.js'

const active = page => page.locator('.workspace-pane[aria-hidden="false"]')
const customerName = 'SYNTH-SALES 森爵界面验收国际商业照明与综合工程采购服务中心 — International Commercial Lighting Project Procurement'
const states = [
  ['C01', '/customers', '客户管理'],
  ['C02', '/customers', '新建客户', 'button', '.customer-editor'],
  ['C03', '/customers?search=SYNTH-SALES-NO-MATCH', '没有符合当前条件的记录'],
  ['C04', '/contacts', '新建联系人', 'button', '.crm-editor'],
  ['C05', '/follow-ups', '新建跟进记录', 'button', '.crm-editor'],
  ['C06', '/new-product-reminders', '客户产品需求'],
  ['Q01', '/quotes', '报价管理'],
  ['Q02', '/quotes', '新建报价', 'button', '.quote-editor-modal'],
  ['O01', '/orders', '订单管理'],
  ['O02', '/orders', '新建订单', 'button', '.modal'],
]

test('sales state evidence in an owned Google Chrome profile', async ({ baseURL }) => {
  test.setTimeout(2400000)
  const root = process.env.ISOLATED_TEST_ROOT
  const output = path.resolve(process.env.SALES_STATE_EVIDENCE_DIR)
  await mkdir(output, { recursive: true })
  const context = await chromium.launchPersistentContext(path.join(root, 'sales-state-chrome'), {
    channel: 'chrome',
    viewport: { width: 1440, height: 900 },
  })
  const results = []
  try {
    const { cookies, origins } = JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8'))
    await context.addCookies(cookies)
    await context.addInitScript(({ origins }) => {
      const stored = origins.find(item => item.origin === location.origin)
      if (stored) for (const item of stored.localStorage) localStorage.setItem(item.name, item.value)
    }, { origins })
    const settings = context.pages()[0]
    context.setDefaultTimeout(150000)
    context.setDefaultNavigationTimeout(100000)
    const page = await context.newPage()
    const cdp = await context.newCDPSession(page)
    const browser = await cdp.send('Browser.getVersion')
    expect(browser.product).toMatch(/^Chrome\//)
    async function capture(id, width, height, zoom) {
      const metrics = await page.evaluate(() => ({
        cssWidth: innerWidth, cssHeight: innerHeight, dpr: devicePixelRatio,
        documentWidth: document.documentElement.scrollWidth,
        topbarBottom: document.querySelector('.topbar')?.getBoundingClientRect().bottom,
        workspaceTop: document.querySelector('.workspace-bar')?.getBoundingClientRect().top,
      }))
      expect(metrics.dpr).toBeCloseTo(zoom, 2)
      expect(metrics.cssWidth).toBeCloseTo(width / zoom, 0)
      const file = id + '-' + width + '-' + zoom * 100 + '.png'
      const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
      await writeFile(path.join(output, file), Buffer.from(data, 'base64'))
      results.push({ id, width, height, zoom, ...metrics, file })
    }

    await page.goto(new URL('/customers', baseURL).href)
    await active(page).getByRole('button', { name: '新建客户', exact: true }).click()
    await active(page).locator('.customer-editor .field').filter({ hasText: '客户名称' }).locator('input').first().fill(customerName)
    await active(page).locator('.contact-create-card .contact-fields input').first().fill('SYNTH-SALES 联系人')
    const saved = page.waitForResponse(response => new URL(response.url()).pathname === '/api/customers/' && response.request().method() === 'POST')
    await active(page).getByRole('button', { name: '保存客户', exact: true }).click()
    const response = await saved
    expect(response.status()).toBe(201)
    const customer = await response.json()
    await expect(page).toHaveURL(new RegExp('[?&]detail=' + customer.id))
    const coreCases = [...states, ['C07', '/customers?detail=' + customer.id, '关闭详情', 'visible-button'], ['C08', '/customers?detail=' + customer.id, '编辑客户', 'button', '.customer-editor']]
    const supplemental = process.env.SALES_STATE_SUPPLEMENTAL === '1'
    const journey = process.env.SALES_STATE_JOURNEYS === '1'
    let fixture
    let cases = coreCases
    if (supplemental || journey) {
      const seed = path.resolve('../docs/uat-evidence/ui-sales-state-evidence-01/seed-synthetic.py')
      fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed, String(customer.id)], { encoding: 'utf8' }))
      const quote = '/quotes?detail=' + fixture.quote
      const order = '/orders?detail=' + fixture.order
      cases = [
        coreCases.find(([id]) => id === 'C04'),
        coreCases.find(([id]) => id === 'C05'),
        ['C05A', '/follow-ups?create=1&customer=' + customer.id, '保存跟进', 'visible-button', null, 'attachments'],
        ['Q06', quote, '关闭报价详情', 'visible-button'],
        ['Q05', quote, '预览 PI', 'button', '.quote-preview-modal'],
        ['Q04', quote, '创建修订版', 'button', '.quote-editor-modal'],
        ['O03', order, '编辑草稿', 'button', '.modal'],
        ['O04', order, '确认订单', 'button', '.app-dialog'],
        ['O05D', order, '关闭订单详情', 'visible-button'],
      ]
    }
    const focused = process.env.SALES_STATE_FOCUSED === '1'
    if (focused) cases = [...(supplemental ? cases : []),
      ['C07R', '/customers?detail=' + customer.id, '编辑客户', 'visible-button'],
      ['C11', '/customers', '', 'failure'],
      ['Q02R', '/quotes', '新建报价', 'button', '.quote-editor-modal'],
    ]
    const caseFilter = process.env.SALES_STATE_CASES?.split(',')
    if (caseFilter) cases = caseFilter.map(id => [...cases, ...coreCases].find(([key]) => key === id)).filter(Boolean)
    const saveIndex = () => writeFile(path.join(output, 'run.json'), JSON.stringify({ browser, customerCreate: response.status(), results }, null, 2))
    if (journey) {
      await recordSalesJourneys({ page, settings, baseURL, fixture, customer, capture, results, saveIndex })
      expect(results.some(result => result.file)).toBe(true)
      if (process.env.A3_STRICT_BROWSER_EVIDENCE === '1') {
        expect(results.filter(result => ['uncaptured', 'incomplete'].includes(result.outcome))).toEqual([])
      }
      return
    }
    await settings.goto('chrome://settings/appearance', { waitUntil: 'domcontentloaded' })
    const zoomLevels = process.env.SALES_STATE_ZOOM ? [Number(process.env.SALES_STATE_ZOOM)] : [1, 1.25]
    for (const zoom of zoomLevels) {
      await settings.locator('settings-appearance-page select').filter({
        has: settings.locator('option[value="1.25"]'),
      }).selectOption(String(zoom))
      for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
        if (process.env.SALES_STATE_WIDTH && Number(process.env.SALES_STATE_WIDTH) !== width) continue
        await page.setViewportSize({ width, height })
        for (const [id, route, label, action, target, preparation] of cases) {
          try {
            const customerList = url => url.pathname === '/api/customers/' && url.searchParams.has('search')
            if (action === 'failure') await page.route(customerList, route => route.abort('failed'))
            await page.goto(new URL(route, baseURL).href, { timeout: 100000 })
            if (id === 'C08') {
              const detail = page.getByRole('dialog', { name: '客户详情', exact: true })
              await expect(detail.getByRole('button', { name: '关闭详情', exact: true })).toBeVisible()
              await detail.getByRole('button', { name: '编辑客户', exact: true }).click()
              const editor = page.getByRole('dialog', { name: '编辑客户', exact: true })
              await expect(editor).toBeVisible({ timeout: 30000 })
              await expect(editor.getByLabel('客户名称')).toHaveValue(customer.name)
            } else if (action === 'button') {
              await page.getByRole('button', { name: label, exact: true }).first().click({ timeout: 25000 })
              await expect(page.locator(target).first()).toBeVisible({ timeout: 20000 })
            } else if (action === 'failure') {
              await expect(page.locator('.page-load-state-error')).toBeVisible()
            } else if (action === 'visible-button') {
              await expect(active(page).getByRole('button', { name: label, exact: true })).toBeVisible({ timeout: 20000 })
            } else {
              await expect(page.getByText(label, { exact: false }).first()).toBeVisible({ timeout: 20000 })
            }
            if (preparation === 'attachments') {
              const files = ['synth-brief.txt', 'synth-follow-up.txt'].map(name => ({
                name, mimeType: 'text/plain', buffer: Buffer.from('Synthetic evidence only.'),
              }))
              await page.locator('.follow-up-attachment-editor input[type="file"]').setInputFiles(files)
              await expect(page.getByText(files[1].name)).toBeVisible()
              await page.getByText(files[1].name).scrollIntoViewIfNeeded()
            }
            await page.evaluate(async () => {
              await Promise.race([document.fonts.ready, new Promise(resolve => setTimeout(resolve, 500))])
              await Promise.race([Promise.allSettled(document.getAnimations().map(animation => animation.finished)), new Promise(resolve => setTimeout(resolve, 400))])
            })
            if (width === 390) {
              await expect.poll(() => page.locator('.sidebar').evaluate(sidebar => sidebar.getBoundingClientRect().right), {
                timeout: 20000,
              }).toBeLessThanOrEqual(1)
            }
            await capture(id, width, height, zoom)
            if (id === 'C08') {
              const editor = page.getByRole('dialog', { name: '编辑客户', exact: true })
              await editor.getByRole('button', { name: '取消', exact: true }).click()
              await expect(editor).toHaveCount(0)
              await expect(page.getByRole('dialog', { name: '客户详情', exact: true })).toBeVisible()
            }
            if (id === 'Q02R') {
              const overflow = await page.evaluate(() => {
                window.scrollTo(10000, 0)
                const offset = scrollX
                const nodes = [...document.querySelectorAll('.quote-editor-modal, .quote-editor-modal .modal-body, .sku-picker-panel')]
                  .map(node => ({ className: node.className, width: node.clientWidth, scrollWidth: node.scrollWidth, overflowX: getComputedStyle(node).overflowX }))
                return { offset, nodes }
              })
              results.at(-1).overflow = overflow
              if (overflow.offset) await capture('Q02X', width, height, zoom)
            }
          } catch (error) {
            results.push({ id, width, height, zoom, outcome: 'uncaptured', reason: String(error.message).split('\n')[0] })
          } finally {
            if (action === 'failure') await page.unrouteAll({ behavior: 'ignoreErrors' })
            await saveIndex()
          }
        }
      }
    }
    expect(results.filter(result => result.file).length).toBeGreaterThan(0)
    if (process.env.A3_STRICT_BROWSER_EVIDENCE === '1') {
      expect(results.filter(result => result.outcome === 'uncaptured')).toEqual([])
    }
  } finally {
    await context.close()
  }
})
