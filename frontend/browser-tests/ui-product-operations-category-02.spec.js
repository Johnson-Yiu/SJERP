import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'

test('category drag persists a new parent, inherited attributes and confirmed sort', async ({ baseURL }) => {
  test.setTimeout(2400000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-category-override')
  await mkdir(output, { recursive: true })
  const seed = fileURLToPath(new URL('../../docs/uat-evidence/ui-product-operations-completion-02/seed.py', import.meta.url))
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.resolve('../backend'), encoding: 'utf8', env: { ...process.env, PRODUCT_OPS_CATEGORY: '1' },
  }))
  const root = process.env.ISOLATED_TEST_ROOT
  const context = await chromium.launchPersistentContext(path.join(root, 'category-order-chrome'), {
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
    const go = () => page.goto(new URL('/categories', baseURL).href, { waitUntil: 'domcontentloaded', timeout: 100000 })
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
    const tree = name => page.locator('.tree-node').filter({ hasText: name })
    const moved = tree('合成待移动分类')
    const target = tree('合成目标分类')
    await page.getByRole('button', { name: '全部展开' }).click()
    await expect(moved).toBeVisible()
    const drag = await page.evaluateHandle(() => new DataTransfer())
    const parentUpdate = page.waitForResponse(r => r.url().endsWith('/api/categories/reorder/') && r.request().method() === 'POST', { timeout: 75000 })
    await moved.dispatchEvent('dragstart', { dataTransfer: drag })
    const childDrop = target.getByTitle('放入此分类成为子分类')
    await expect(childDrop).toBeVisible()
    await childDrop.dispatchEvent('dragover', { dataTransfer: drag })
    await childDrop.dispatchEvent('drop', { dataTransfer: drag })
    const changed = await parentUpdate
    expect(changed.ok(), await changed.text()).toBeTruthy()
    const fetchMoved = async () => {
      const reply = await page.request.get(new URL('/api/categories/' + fixture.category_move + '/', baseURL).href)
      expect(reply.ok()).toBeTruthy()
      return reply.json()
    }
    expect(Number((await fetchMoved()).parent)).toBe(fixture.category_target)
    await go()
    await page.getByRole('button', { name: '全部展开' }).click()
    await moved.click()
    const card = page.locator('.config-panel')
    await expect(card.getByRole('heading', { name: '合成待移动分类' })).toBeVisible()
    const inherited = card.getByRole('row').filter({ hasText: '外壳工艺' })
    await expect(inherited).toContainText('合成目标分类')
    await expect(inherited.getByRole('checkbox').first()).toBeDisabled()
    await inherited.scrollIntoViewIfNeeded()
    await snap('category-inherits-new-parent', { method: 'DOM drag events, real Django reorder' })

    const from = card.getByRole('row').filter({ hasText: '灯罩形式' })
    const to = card.getByRole('row').filter({ hasText: '接线方式' })
    const reorderDrag = await page.evaluateHandle(() => new DataTransfer())
    await from.locator('.attribute-drag-handle').dispatchEvent('dragstart', { dataTransfer: reorderDrag })
    await to.dispatchEvent('drop', { dataTransfer: reorderDrag })
    const review = page.locator('.reorder-review-modal')
    await expect(review.getByRole('heading', { name: '确认参数顺序调整' })).toBeVisible()
    await snap('category-attribute-reorder-preview', { method: 'DOM drag events, real Django preview' })
    await review.getByRole('button', { name: '确认并更新 SKU', exact: true }).click()
    await expect(review).toHaveCount(0)
    await expect.poll(async () => (await fetchMoved()).attributes.map(attribute => attribute.name)).toEqual(['灯罩形式', '接线方式'])
    await go()
    await page.getByRole('button', { name: '全部展开' }).click()
    await moved.click()
    await expect(card.locator('tbody tr:not(.inherited)').first()).toContainText('灯罩形式')
    await card.locator('tbody tr:not(.inherited)').first().scrollIntoViewIfNeeded()
    await snap('category-attribute-order-reopened')
    await card.getByRole('button', { name: '新增属性' }).click()
    const newAttribute = card.getByPlaceholder('输入属性名称，例如：色温')
    await newAttribute.fill('外壳工艺')
    const [override] = await Promise.all([
      page.waitForResponse(r => r.url().endsWith('/api/category-attributes/') && r.request().method() === 'POST', { timeout: 75000 }),
      newAttribute.press('Enter'),
    ])
    expect(override.status(), await override.text()).toBe(201)
    const overrideId = (await override.json()).id
    await go()
    await page.getByRole('button', { name: '全部展开' }).click()
    await moved.click()
    const shadowed = card.getByRole('row').filter({ hasText: '外壳工艺' })
    await expect(shadowed).toHaveCount(1)
    await expect(shadowed).toContainText('当前分类')
    await expect(shadowed.getByRole('checkbox').first()).toBeEnabled()
    const effective = (await fetchMoved()).effective_attributes.filter(attribute => attribute.key === '外壳工艺')
    expect(effective).toHaveLength(1)
    expect(effective[0]).toMatchObject({ id: overrideId, inherited: false })
    await shadowed.scrollIntoViewIfNeeded()
    await snap('category-override-reopened')
  } catch (error) {
    failure = String(error.message)
    throw error
  } finally {
    await save()
    await context.close()
  }
})
