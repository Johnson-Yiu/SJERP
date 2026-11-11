import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'

test('product parameter survives save and reopen and shared sales/history chrome stays aligned', async ({ baseURL }) => {
  test.setTimeout(2400000)
  const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT)
  const output = path.join(evidence, 'chrome-customer-edit')
  await mkdir(output, { recursive: true })
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [fileURLToPath(new URL('../../docs/uat-evidence/ui-product-operations-completion-02/seed.py', import.meta.url))], {
    cwd: path.resolve('../backend'), encoding: 'utf8',
  }))
  const root = process.env.ISOLATED_TEST_ROOT
  const context = await chromium.launchPersistentContext(path.join(root, 'product-cross-check-chrome'), {
    channel: 'chrome', viewport: { width: 390, height: 844 },
  })
  const states = []
  let browser
  let failure
  const save = () => writeFile(path.join(output, 'run.json'), JSON.stringify({ source, browser, api: 'real isolated Django', states, failure }, null, 2) + '\n')
  try {
    const auth = JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8'))
    await context.addCookies(auth.cookies)
    const settings = context.pages()[0]
    const page = await context.newPage()
    page.setDefaultTimeout(30000)
    const cdp = await context.newCDPSession(page)
    browser = (await cdp.send('Browser.getVersion')).product
    expect(browser).toMatch(/^Chrome\//)
    async function go(route) {
      await page.goto(new URL(route, baseURL).href, { waitUntil: 'commit', timeout: 100000 })
    }
    async function snap(id, zoom, metrics = {}) {
      const dpr = await page.evaluate(() => devicePixelRatio)
      expect(dpr).toBeCloseTo(zoom, 2)
      const png = id + '-390-' + zoom * 100 + '.png'
      const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
      await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
      states.push({ id, width: 390, height: 844, zoom, dpr, png, ...metrics })
      await save()
    }
    await settings.goto('chrome://settings/appearance', { waitUntil: 'domcontentloaded', timeout: 100000 })
    const zoomControl = settings.locator('settings-appearance-page select').filter({ has: settings.locator('option[value="1.25"]') })
    await zoomControl.selectOption('1.25')
    await go('/product-parameters')
    await page.getByRole('button', { name: '新建产品参数', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: '新建产品参数' })
    await dialog.getByLabel('所属产品').selectOption(String(fixture.product))
    await dialog.getByLabel('参数名称').fill('合成额定输入')
    await dialog.getByLabel('参数值').fill('48')
    await dialog.getByLabel('单位', { exact: true }).fill('V')
    const [response] = await Promise.all([
      page.waitForResponse(r => new URL(r.url()).pathname === '/api/product-parameters/' && r.request().method() === 'POST', { timeout: 75000 }),
      dialog.getByRole('button', { name: '保存', exact: true }).click(),
    ])
    states.push({ id: 'parameter-post', status: response.status() })
    await save()
    expect(response.status()).toBe(201)
    await expect(dialog).toHaveCount(0)
    await go('/product-parameters')
    await page.reload({ waitUntil: 'domcontentloaded' })
    const row = page.getByRole('row').filter({ hasText: '合成额定输入' })
    await row.getByRole('button', { name: '编辑', exact: true }).click()
    const reopened = page.getByRole('dialog', { name: '编辑产品参数' })
    await expect(reopened.getByLabel('参数值')).toHaveValue('48')
    await expect(reopened.getByLabel('单位', { exact: true })).toHaveValue('V')
    await reopened.getByLabel('参数值').scrollIntoViewIfNeeded()
    await snap('parameter-reopened', 1.25)

    for (const zoom of [1, 1.25]) {
      await zoomControl.selectOption(String(zoom))
      for (const [route, title, id] of [
        ['/customers', '客户管理', 'sales-customers'],
        ['/historical-orders', '历史订单分析', 'history-analysis'],
      ]) {
        await go(route)
        await expect(page.locator('.topbar').getByRole('heading', { name: title, exact: true })).toBeVisible()
        await expect(page.locator('.workspace-tab.active')).toContainText(title)
        const metrics = await page.evaluate(() => ({
          topbarBottom: document.querySelector('.topbar').getBoundingClientRect().bottom,
          workspaceTop: document.querySelector('.workspace-bar').getBoundingClientRect().top,
          cssWidth: innerWidth,
        }))
        await snap(id, zoom, metrics)
        expect(metrics.workspaceTop).toBeCloseTo(metrics.topbarBottom, 0)
        if (route === '/customers') {
          await page.getByRole('row').filter({ hasText: '合成采购成本归属客户' }).click()
          const detail = page.getByRole('dialog', { name: '客户详情' })
          const edit = detail.getByRole('button', { name: '编辑客户', exact: true })
          await expect(edit).toBeInViewport()
          await snap('customer-detail-edit-action', zoom)
          await edit.click()
          const editor = page.getByRole('dialog', { name: '编辑客户' })
          await expect(editor).toBeVisible()
          await expect(editor.getByLabel('客户名称')).toHaveValue('合成采购成本归属客户')
          await snap('customer-detail-edit-opened', zoom)
          await editor.getByRole('button', { name: '取消', exact: true }).click()
          await expect(editor).toHaveCount(0)
        }
      }
    }
  } catch (error) {
    failure = String(error.message)
    throw error
  } finally {
    await save()
    await context.close()
  }
})
