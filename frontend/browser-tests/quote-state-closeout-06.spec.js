import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'

test('Q6 quote search, validation and workbook download', async ({ baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== 'quote-state-closeout-06.spec.js', 'Run the dedicated Q6 isolation profile.')
  test.setTimeout(900000)
  const repository = fileURLToPath(new URL('../../', import.meta.url))
  const evidence = path.join(repository, 'docs/uat-evidence/quote-state-closeout-06')
  const root = process.env.ISOLATED_TEST_ROOT
  expect(root).toBeTruthy()
  expect(process.env.ISOLATED_CODEX_TEST_SUPERADMIN).toBe('1')
  const python = process.env.ISOLATED_TEST_PYTHON
  const backend = path.join(repository, 'backend')
  const fixture = JSON.parse(execFileSync(python, [path.join(evidence, 'seed.py')], { cwd: backend, encoding: 'utf8' }))
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repository, encoding: 'utf8' }).trim()
  const screenshots = path.join(evidence, 'screenshots')
  await mkdir(screenshots, { recursive: true })
  const context = await chromium.launchPersistentContext(path.join(root, 'q6-chrome'), { channel: 'chrome', acceptDownloads: true })
  const results = []
  let browser
  try {
    const auth = JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8'))
    await context.addCookies(auth.cookies)
    const settings = context.pages()[0]
    const page = await context.newPage()
    page.setDefaultTimeout(15000)
    const session = await page.request.get(new URL('/api/session/current-operator/', baseURL).href)
    expect(await session.json()).toMatchObject({ name: 'codex', authenticated: true })
    const cdp = await context.newCDPSession(page)
    browser = (await cdp.send('Browser.getVersion')).product
    expect(browser).toMatch(/^Chrome\//)
    await settings.goto('chrome://settings/appearance', { waitUntil: 'commit' })
    const zoomControl = settings.locator('settings-appearance-page select').filter({
      has: settings.locator('option[value="1.25"]'),
    })
    for (const zoom of [1, 1.25]) {
      await settings.bringToFront()
      await zoomControl.selectOption(String(zoom))
      await page.bringToFront()
      for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
        const name = `${width}-${zoom * 100}`
        try {
          const capture = async state => {
            const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' })
            await writeFile(path.join(screenshots, `${state}-${name}.png`), Buffer.from(data, 'base64'))
          }
          await page.setViewportSize({ width, height })
          await page.goto(new URL(`/quotes?create=1&customer=${fixture.customer}`, baseURL).href, { waitUntil: 'domcontentloaded' })
          const editor = page.locator('form.quote-editor-modal')
          await expect(editor).toBeVisible()
          const metrics = await page.evaluate(() => ({ dpr: devicePixelRatio, cssWidth: innerWidth }))
          expect(metrics.dpr).toBe(zoom)
          expect(metrics.cssWidth).toBeCloseTo(width / zoom, 0)
          const search = editor.getByRole('searchbox')
          await search.fill('Q6-NO-MATCH')
          await expect(editor.getByText('没有匹配的 SKU。')).toBeVisible()
          await capture('no-match')
          await search.fill('Q6-BOX')
          await editor.locator('.sku-picker-options label').filter({ hasText: 'Q6-BOX' }).locator('input').check()
          await search.fill('Q6-EACH')
          const eachChoice = editor.locator('.sku-picker-options label').filter({ hasText: 'Q6-EACH' }).locator('input')
          await eachChoice.scrollIntoViewIfNeeded()
          await capture('second-choice')
          await eachChoice.check()
          const boxLine = editor.locator('.quote-line-row').filter({ hasText: 'Q6-BOX' })
          const eachLine = editor.locator('.quote-line-row').filter({ hasText: 'Q6-EACH' })
          await boxLine.getByLabel('交易单位与包装规格').selectOption(String(fixture.box))
          await boxLine.getByLabel('数量').fill('2')
          await eachLine.getByLabel('数量').fill('3')
          const inventory = editor.locator('.quote-inventory-row')
          const boxRisk = inventory.filter({ hasText: 'Q6-BOX' })
          const eachRisk = inventory.filter({ hasText: 'Q6-EACH' })
          await expect(boxRisk).toContainText('缺口：5 pcs')
          await expect(boxRisk.locator('dl div').filter({ hasText: '本报价需求' })).toContainText('20 pcs')
          await expect(eachRisk).toContainText('库存可覆盖')
          await expect(eachRisk.locator('dl div').filter({ hasText: '本报价需求' })).toContainText('3 pcs')
          await boxRisk.scrollIntoViewIfNeeded()
          await capture('stock')
          const price = eachLine.getByLabel('单价')
          const model = boxLine.getByLabel('报价型号')
          const save = editor.getByRole('button', { name: '保存报价', exact: true })
          const isSave = response => new URL(response.url()).pathname === '/api/quotes/' && response.request().method() === 'POST'
          await price.fill('-1')
          await save.click()
          expect(await price.evaluate(input => input.validity.rangeUnderflow)).toBe(true)
          await expect(price).toBeFocused()
          await capture('price')
          await price.fill('13.25')
          await model.fill('Q'.repeat(81))
          const rejected = page.waitForResponse(isSave)
          await save.click()
          const rejection = await rejected
          expect(rejection.status()).toBe(400)
          expect(JSON.stringify(await rejection.json())).toContain('sales_model_snapshot')
          await expect(editor.locator('.quote-message.error')).toContainText('报价型号')
          await expect(model).toBeFocused()
          await capture('model')
          await model.fill('Q6-BOX-CORRECTED')
          const saved = page.waitForResponse(isSave)
          await save.click()
          const response = await saved
          expect(response.status()).toBe(201)
          const quote = await response.json()
          await expect(editor).toHaveCount(0)
          await page.goto(new URL(`/quotes?detail=${quote.id}`, baseURL).href, { waitUntil: 'domcontentloaded' })
          const detail = page.getByRole('dialog', { name: '报价工作台' })
          await expect(detail).toContainText(quote.quote_no)
          const reloaded = await page.request.get(new URL(`/api/quotes/${quote.id}/`, baseURL).href)
          expect(reloaded.ok()).toBe(true)
          expect((await reloaded.json()).items).toEqual(expect.arrayContaining([
            expect.objectContaining({ sales_model_snapshot: 'Q6-BOX-CORRECTED' }),
            expect.objectContaining({ sales_model_snapshot: 'Q6-EACH-MODEL', unit_price: expect.stringMatching(/^13\.25/) }),
          ]))
          const exportButton = detail.getByRole('button', { name: '导出 Excel', exact: true })
          const risk = page.getByRole('dialog', { name: '导出前风险提示' })
          const downloads = path.join(evidence, 'downloads')
          await mkdir(downloads, { recursive: true })
          async function exportVersion(version, failFirst) {
            const endpoint = url => url.pathname === `/api/quotes/${version.id}/export/`
            let requests = 0
            const count = request => {
              if (request.method() === 'GET' && endpoint(new URL(request.url()))) requests++
            }
            page.on('request', count)
            try {
              await exportButton.click()
              await expect(risk).toContainText('Q6-BOX')
              await risk.getByRole('button', { name: '暂不导出' }).click()
              await expect(risk).toHaveCount(0)
              expect(requests).toBe(0)
              if (failFirst) {
                await page.route(endpoint, route => route.request().method() === 'GET'
                  ? route.fulfill({ status: 400, json: { detail: 'Q6 合成导出故障' } })
                  : route.continue())
                try {
                  await exportButton.click()
                  await risk.getByRole('button', { name: '了解风险，继续导出' }).click()
                  await expect(detail.getByText('Q6 合成导出故障')).toBeVisible()
                  expect(requests).toBe(1)
                  await capture('export-rejected')
                } finally {
                  await page.unroute(endpoint)
                }
              }
              await exportButton.click()
              await capture(failFirst ? 'revision-export-risk' : 'original-export-risk')
              const downloaded = page.waitForEvent('download')
              const exported = page.waitForResponse(response => endpoint(new URL(response.url())) && response.request().method() === 'GET')
              await risk.getByRole('button', { name: '了解风险，继续导出' }).click()
              expect((await exported).status()).toBe(200)
              const download = await downloaded
              expect(download.suggestedFilename()).toContain(version.quote_no)
              const file = path.join(downloads, `${name}-v${version.revision_no}.xlsx`)
              await download.saveAs(file)
              const pi = await page.request.get(new URL(`/api/quotes/${version.id}/pi-data/`, baseURL).href)
              expect(pi.ok()).toBe(true)
              const content = await pi.json()
              expect(content.invoice_no).toBe(version.quote_no)
              expect(content.buyer.company_name).toBe('Q6 Synthetic Buyer')
              const workbook = JSON.parse(execFileSync(python, [path.join(evidence, 'verify_download.py'), file], {
                input: JSON.stringify(content), encoding: 'utf8',
              }))
              return { ...workbook, revision: version.revision_no, requests }
            } finally {
              page.off('request', count)
            }
          }
          expect(quote.revision_no).toBe(0)
          const original = await exportVersion(quote, false)
          await detail.getByRole('button', { name: '主体更正', exact: true }).click()
          await expect(detail.getByText(/当前报价状态不可操作/)).toBeVisible()
          await expect(detail.getByRole('button', { name: '提交更正申请' })).toBeDisabled()
          await capture('party-draft')
          const marked = page.waitForResponse(response => new URL(response.url()).pathname === `/api/quotes/${quote.id}/mark-sent/` && response.request().method() === 'POST')
          await detail.getByRole('button', { name: '标记为已发送' }).click()
          expect((await marked).status()).toBe(200)
          await detail.getByRole('button', { name: '主体更正', exact: true }).click()
          await detail.locator('#party-address').fill('Q6 Synthetic Corrected Address')
          await detail.getByLabel('原因', { exact: true }).fill('Q6 correction reason')
          await detail.getByLabel('依据', { exact: true }).fill('Q6 synthetic source')
          await detail.getByLabel('我已核对依据，确认法律主体未变').check()
          const proposal = page.waitForResponse(response => new URL(response.url()).pathname === `/api/quotes/${quote.id}/party-change/` && response.request().method() === 'POST')
          await detail.getByRole('button', { name: '提交更正申请' }).click()
          expect((await proposal).status()).toBe(201)
          await expect(detail.getByText('申请人不能审批自己的申请。')).toBeVisible()
          await expect(detail.getByRole('button', { name: '批准更正', exact: true })).toHaveCount(0)
          await capture('party-pending')
          await detail.getByLabel('处理原因', { exact: true }).fill('Q6 synthetic withdrawal')
          const withdrawal = page.waitForResponse(response => new URL(response.url()).pathname.startsWith(`/api/quotes/${quote.id}/`) && new URL(response.url()).pathname.endsWith('/withdraw/') && response.request().method() === 'POST')
          await detail.getByRole('button', { name: '撤回申请' }).click()
          expect((await withdrawal).status()).toBe(200)
          await expect(detail.getByText(/已撤回.*Q6 synthetic withdrawal/)).toBeVisible()
          await capture('party-withdrawn')
          await detail.locator('#party-address').fill('Q6 Synthetic Second Address')
          await detail.getByLabel('原因', { exact: true }).fill('Q6 second correction reason')
          await detail.getByLabel('依据', { exact: true }).fill('Q6 synthetic source')
          await detail.getByLabel('我已核对依据，确认法律主体未变').check()
          const secondProposal = page.waitForResponse(response => new URL(response.url()).pathname === `/api/quotes/${quote.id}/party-change/` && response.request().method() === 'POST')
          await detail.getByRole('button', { name: '提交更正申请' }).click()
          expect((await secondProposal).status()).toBe(201)
          await detail.getByLabel('处理原因', { exact: true }).fill('Q6 synthetic invalidation')
          const invalidation = page.waitForResponse(response => new URL(response.url()).pathname.startsWith(`/api/quotes/${quote.id}/`) && new URL(response.url()).pathname.endsWith('/invalidate/') && response.request().method() === 'POST')
          await detail.getByRole('button', { name: '标记失效' }).click()
          expect((await invalidation).status()).toBe(200)
          await expect(detail.getByText(/已失效.*Q6 synthetic invalidation/)).toBeVisible()
          await capture('party-invalidated')
          await detail.getByRole('button', { name: '创建修订版' }).click()
          await editor.locator('.revision-summary textarea').fill('Q6 revision with changed quantity')
          await eachLine.getByLabel('数量').fill('4')
          const revised = page.waitForResponse(response => new URL(response.url()).pathname === `/api/quotes/${quote.id}/revise/` && response.request().method() === 'POST')
          await save.click()
          const revisionResponse = await revised
          expect(revisionResponse.status()).toBe(201)
          const revision = await revisionResponse.json()
          expect(revision.revision_no).toBe(1)
          await page.goto(new URL(`/quotes?detail=${revision.id}`, baseURL).href, { waitUntil: 'domcontentloaded' })
          await expect(detail).toContainText(revision.quote_no)
          const revisedWorkbook = await exportVersion(revision, true)
          expect(revisedWorkbook.quote).not.toBe(original.quote)
          expect(revisedWorkbook.total).not.toBe(original.total)
          expect(revisedWorkbook.template_sha256).toBe(original.template_sha256)
          results.push({ width, height, zoom, ...metrics, search: true, stock: true, price: true, model: true,
            party: { draft: true, proposal: 201, withdrawal: 200, invalidation: 200 }, workbooks: [original, revisedWorkbook] })
        } catch (error) {
          results.push({ width, height, zoom, failure: String(error.message).split('\n')[0] })
          console.error(`Q6 ${name}: ${error.message}`)
        }
      }
    }
    expect(results.filter(result => result.failure)).toEqual([])
  } finally {
    await context.close()
    await writeFile(path.join(evidence, 'run.json'), JSON.stringify({ source, browser, results }, null, 2) + '\n')
  }
})
