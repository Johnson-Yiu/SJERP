import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'

const sizes = [[1366, 768], [1440, 900], [390, 844]]

test('product detail fits the available workspace and nested details restore focus', async ({ baseURL }) => {
  test.setTimeout(2400000)
  const root = process.env.ISOLATED_TEST_ROOT
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  if (process.env.PRODUCT_OPS_SOURCE_SHA) expect(source).toBe(process.env.PRODUCT_OPS_SOURCE_SHA)
  const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT)
  const output = path.join(evidence, process.env.PRODUCT_OPS_RUN || 'chrome-product-detail')
  await mkdir(output, { recursive: true })
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [fileURLToPath(new URL('../../docs/uat-evidence/ui-product-operations-completion-02/seed.py', import.meta.url))], {
    cwd: path.resolve('../backend'), encoding: 'utf8',
  }))
  const context = await chromium.launchPersistentContext(path.join(root, 'product-detail-chrome'), {
    channel: 'chrome', viewport: { width: 1440, height: 900 },
  })
  const states = []
  const failures = []
  let browser
  const save = () => writeFile(path.join(output, 'run.json'), JSON.stringify({ source, browser, api: 'real isolated Django', states, failures }, null, 2) + '\n')
  try {
    const auth = JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8'))
    await context.addCookies(auth.cookies)
    const settings = context.pages()[0]
    const page = await context.newPage()
    page.setDefaultTimeout(30000)
    const cdp = await context.newCDPSession(page)
    browser = (await cdp.send('Browser.getVersion')).product
    expect(browser).toMatch(/^Chrome\//)
    await settings.goto('chrome://settings/appearance', { waitUntil: 'domcontentloaded', timeout: 100000 })
    const zoomControl = settings.locator('settings-appearance-page select').filter({
      has: settings.locator('option[value="1.25"]'),
    })
    const product = page.locator('.workspace-pane[aria-hidden="false"] .product-detail-modal')
    const dialog = page.locator('.workspace-pane[aria-hidden="false"] .product-context-drawer [role="dialog"]')
    const row = page.locator('.workspace-pane[aria-hidden="false"] .product-list-table').getByRole('row').filter({ hasText: 'EVID-P001' })
    async function capture(id, width, height, zoom, geometry = {}) {
      const png = id + '-' + width + '-' + zoom * 100 + '.png'
      const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
      await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
      states.push({ id, width, height, zoom, ...geometry, png })
      await save()
    }
    for (const zoom of [1, 1.25]) {
      await zoomControl.selectOption(String(zoom))
      for (const [width, height] of sizes) {
        try {
          await page.setViewportSize({ width, height })
          await page.goto(new URL('/products', baseURL).href, { waitUntil: 'commit', timeout: 100000 })
          await row.focus()
          await row.press('Enter')
          await expect(product.getByRole('heading', { name: /合成长名称.*多场景安装配件组合/ })).toBeVisible()
          const card = product.getByRole('heading', { name: '基础信息', exact: true })
          await expect(card).toBeVisible()
          await expect.poll(() => product.evaluate(element => element.getAnimations().filter(animation => animation.playState === 'running').length)).toBe(0)
          const geometry = await product.evaluate(element => ({
            left: element.getBoundingClientRect().left,
            right: element.getBoundingClientRect().right,
            availableLeft: element.parentElement.getBoundingClientRect().left,
            availableRight: element.parentElement.getBoundingClientRect().right,
            titleLeft: element.querySelector('h2').getBoundingClientRect().left,
            cardLeft: element.querySelector('.workspace-card').getBoundingClientRect().left,
            dpr: devicePixelRatio, cssWidth: innerWidth,
            documentWidth: document.documentElement.scrollWidth,
          }))
          await capture('product-overview', width, height, zoom, geometry)
          expect(geometry.dpr).toBeCloseTo(zoom, 2)
          expect(geometry.cssWidth).toBeCloseTo(width / zoom, 0)
          expect(geometry.left).toBeGreaterThanOrEqual(geometry.availableLeft - 1)
          expect(geometry.right).toBeLessThanOrEqual(geometry.availableRight + 1)
          expect(geometry.titleLeft).toBeGreaterThanOrEqual(geometry.availableLeft)
          expect(geometry.cardLeft).toBeGreaterThanOrEqual(geometry.availableLeft)
          expect(Number(new URL(page.url()).searchParams.get('detail'))).toBe(fixture.product)
          const scroll = await product.evaluate(element => {
            const available = element.scrollHeight - element.clientHeight
            element.scrollTop = 100
            const moved = element.scrollTop
            element.scrollTop = 0
            return { available, moved }
          })
          if (scroll.available > 0) expect(scroll.moved).toBeGreaterThan(0)
          const activeTab = page.locator('.workspace-tab.active [role="tab"]')
          const workspaceTitle = await activeTab.innerText()
          const tabs = product.getByRole('navigation', { name: '产品详情导航' })
          await tabs.getByRole('button', { name: /证书/ }).click()
          const trigger = product.locator('.context-drill').first()
          await trigger.focus()
          await trigger.press('Enter')
          await expect(dialog.getByRole('heading', { name: '合成测试证书', exact: true })).toBeVisible()
          const close = dialog.getByRole('button', { name: '关闭详情' })
          await expect(close).toBeFocused()
          const nestedGeometry = await dialog.evaluate(element => ({
            top: element.getBoundingClientRect().top,
            availableTop: element.parentElement.parentElement.getBoundingClientRect().top,
          }))
          await capture('product-nested-certificate', width, height, zoom, nestedGeometry)
          expect(nestedGeometry.top).toBeCloseTo(nestedGeometry.availableTop, 0)
          await expect(activeTab).toHaveText(workspaceTitle)
          await close.press(zoom === 1.25 ? 'Escape' : 'Enter')
          await expect(dialog).toHaveCount(0)
          await expect(trigger).toBeFocused()
          await expect(tabs.getByRole('button', { name: /证书/ })).toHaveClass(/active/)
          await product.getByRole('button', { name: '关闭详情' }).click()
          await expect(product).toHaveCount(0)
          await expect(row).toBeFocused()
        } catch (error) {
          failures.push({ width, height, zoom, message: String(error.message) })
          await save()
        }
      }
    }
    expect(failures).toEqual([])
  } finally {
    await save()
    await context.close()
  }
})
