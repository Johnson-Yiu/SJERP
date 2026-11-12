import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'

test('Q6 independently reviews existing quote party requests', async ({ baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== 'quote-state-closeout-06-review.spec.js', 'Run the Q6 party review profile.')
  test.setTimeout(900000)
  const repository = fileURLToPath(new URL('../../', import.meta.url))
  const evidence = path.join(repository, 'docs/uat-evidence/quote-state-closeout-06')
  const root = process.env.ISOLATED_TEST_ROOT
  expect(root).toBeTruthy()
  expect(process.env.ISOLATED_CODEX_TEST_SUPERADMIN).toBe('1')
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [path.join(evidence, 'seed_review.py')], {
    cwd: path.join(repository, 'backend'), encoding: 'utf8',
  }))
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repository, encoding: 'utf8' }).trim()
  const screenshots = path.join(evidence, 'review')
  await mkdir(screenshots, { recursive: true })
  const context = await chromium.launchPersistentContext(path.join(root, 'q6-review-chrome'), { channel: 'chrome' })
  const results = []
  try {
    await context.addCookies(JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8')).cookies)
    const settings = context.pages()[0]
    const page = await context.newPage()
    page.setDefaultTimeout(15000)
    const operator = await page.request.get(new URL('/api/session/current-operator/', baseURL).href)
    expect(await operator.json()).toMatchObject({ name: 'codex', authenticated: true })
    const cdp = await context.newCDPSession(page)
    const browser = (await cdp.send('Browser.getVersion')).product
    expect(browser).toMatch(/^Chrome\//)
    await settings.goto('chrome://settings/appearance', { waitUntil: 'commit' })
    const zoomControl = settings.locator('settings-appearance-page select').filter({
      has: settings.locator('option[value="1.25"]'),
    })
    let index = 0
    for (const zoom of [1, 1.25]) {
      await settings.bringToFront()
      await zoomControl.selectOption(String(zoom))
      await page.bringToFront()
      for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
        await page.setViewportSize({ width, height })
        for (const [action, { quote, proposal }] of Object.entries(fixture.cases[index])) {
          try {
            await page.goto(new URL(`/quotes?detail=${quote}`, baseURL).href, { waitUntil: 'domcontentloaded' })
            expect(await page.evaluate(() => devicePixelRatio)).toBe(zoom)
            const detail = page.getByRole('dialog', { name: '报价工作台' })
            await detail.getByRole('button', { name: '主体更正', exact: true }).click()
            const request = detail.locator('.party-request')
            await expect(request).toContainText('待审批')
            const post = async (operation, button) => {
              const endpoint = `/api/quotes/${quote}/party-change/${proposal}/${operation}/`
              const [response] = await Promise.all([
                page.waitForResponse(r => new URL(r.url()).pathname === endpoint && r.request().method() === 'POST'),
                button.click(),
              ])
              expect(response.status(), await response.text()).toBe(200)
              return response.json()
            }
            if (action === 'reject') {
              await request.getByLabel('处理原因').fill('Q6 independent rejection')
              await post('reject', request.getByRole('button', { name: '拒绝申请' }))
              await expect(request).toContainText('已拒绝')
            } else {
              await request.getByLabel('审批意见').fill('Q6 independent approval')
              const approve = action === 'replace' ? '批准主体替换记录' : '批准更正'
              await post('approve', request.getByRole('button', { name: approve, exact: true }))
              await expect(request).toContainText('已批准')
              if (action === 'invalidate') {
                await request.getByLabel('处理原因').fill('Q6 approved request invalidation')
                await post('invalidate', request.getByRole('button', { name: '标记失效' }))
                await expect(request).toContainText('已失效')
              } else if (action === 'apply') {
                const applied = await post('apply', request.getByRole('button', { name: '生成报价草稿' }))
                const saved = await page.request.get(new URL(`/api/quotes/${applied.result_quote_id}/`, baseURL).href)
                expect(await saved.json()).toMatchObject({ status: 'draft', buyer_address: 'Q6 approved address' })
                await expect(detail).toContainText('草稿')
              } else {
                await request.getByRole('button', { name: '填写关联新单' }).click()
                const draft = request.locator('.replacement-form')
                await draft.getByLabel('单据日期').fill('2026-11-12')
                await draft.getByLabel('币种').fill('USD')
                await draft.getByLabel('汇率').fill('7.2')
                await draft.getByLabel('运费').fill('0')
                await draft.getByLabel('折扣').fill('0')
                await draft.getByLabel('定金比例').fill('0.3')
                await draft.getByLabel('SKU').selectOption(String(fixture.sku))
                await draft.getByLabel('数量').fill('3')
                await draft.getByLabel('单价').fill('5')
                await draft.getByLabel('已核对全部新单资料和条款').check()
                const linked = await post('create-replacement', draft.getByRole('button', { name: '创建关联草稿' }))
                const saved = await page.request.get(new URL(`/api/quotes/${linked.result_quote_id}/`, baseURL).href)
                expect(await saved.json()).toMatchObject({ status: 'draft', customer: fixture.target })
              }
            }
            if (action !== 'apply') await request.scrollIntoViewIfNeeded()
            const file = `${action}-${width}-${zoom * 100}.png`
            const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' })
            await writeFile(path.join(screenshots, file), Buffer.from(data, 'base64'))
            results.push({ width, height, zoom, browser, action, file, status: 200 })
          } catch (error) {
            results.push({ width, height, zoom, browser, action, failure: error.message })
          }
        }
        index++
      }
    }
  } finally {
    await writeFile(path.join(evidence, 'review-run.json'), JSON.stringify({ source, results }, null, 2) + '\n')
    await context.close()
  }
  expect(results.filter(result => result.failure)).toEqual([])
})
