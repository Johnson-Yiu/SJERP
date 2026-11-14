import { expect, test } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'

if (process.env.EXPORT_STABILITY_CHROME === '1') test.use({ channel: 'chrome' })

const evidenceDir = path.resolve(process.env.R1_UX_QUOTE_ACTIONS_EVIDENCE_DIR || '')
if (!process.env.R1_UX_QUOTE_ACTIONS_EVIDENCE_DIR) {
  throw new Error('R1_UX_QUOTE_ACTIONS_EVIDENCE_DIR must point to the task evidence directory.')
}

test('quote editor actions stay readable at desktop and narrow widths and preserve preview/save/export', async ({ page }, testInfo) => {
  // Four viewport screenshots plus two full editor visits share this test.
  // Bound each screenshot independently and retain lifecycle diagnostics if
  // the whole workflow or a download fails under a loaded local environment.
  test.setTimeout(90_000)
  const started = Date.now()
  const context = page.context()
  let contextClosed = false
  let observedDownload = null
  let failureMessage = null
  const apiResponses = []
  const emit = (event, extra = {}) => console.log('QUOTE_LIFECYCLE ' + JSON.stringify({ event, elapsedMs: Date.now() - started, processId: process.pid, ...extra }))
  await page.exposeFunction('__quoteDownloadDiagnostic', (event, details) => emit(event, details))
  await page.addInitScript(() => {
    const revoke = URL.revokeObjectURL.bind(URL)
    URL.revokeObjectURL = value => {
      if (String(value).startsWith('blob:')) void window.__quoteDownloadDiagnostic('blob-revoke', {})
      return revoke(value)
    }
    document.addEventListener('click', event => {
      const link = event.target instanceof Element ? event.target.closest('a[download]') : null
      if (link) void window.__quoteDownloadDiagnostic('download-anchor-click', { scheme: link.href.split(':')[0] })
    }, true)
  })
  page.on('framenavigated', frame => { if (frame === page.mainFrame()) emit('main-frame-navigation', { url: frame.url() }) })
  page.on('requestfailed', request => {
    if (request.url().startsWith('blob:') || request.url().includes('/api/quotes/')) emit('request-failed', { scheme: request.url().split(':')[0], failure: request.failure()?.errorText })
  })
  page.on('close', () => emit('page-close'))
  page.on('crash', () => emit('page-crash'))
  context.on('close', () => { contextClosed = true; emit('context-close') })
  page.on('download', download => { observedDownload = download; emit('download-start', { filename: download.suggestedFilename() }) })
  try {
  await fs.mkdir(evidenceDir, { recursive: true })
  const fixture = JSON.parse(await fs.readFile(path.join(evidenceDir, 'fixture.json'), 'utf8'))
  expect(fixture.synthetic_only).toBe(true)
  page.on('response', response => {
    if (new URL(response.url()).pathname.startsWith('/api/quotes/')) {
      apiResponses.push({ method: response.request().method(), path: new URL(response.url()).pathname, status: response.status() })
    }
  })

  async function openEditor() {
    await page.goto(`/quotes?create=1&customer=${fixture.customer}`, { waitUntil: 'domcontentloaded' })
    const editor = page.locator('form.quote-editor-modal')
    await expect(editor).toBeVisible()
    await expect(editor.locator('.quote-action-save-export')).toBeVisible()
    return editor
  }

  // The original cancel action remains available and closes a clean editor.
  await page.setViewportSize({ width: 1440, height: 1000 })
  let editor = await openEditor()
  await editor.getByRole('button', { name: '取消', exact: true }).click()
  await expect(editor).toHaveCount(0)

  editor = await openEditor()
  await editor.locator('.sku-picker-options label').filter({ hasText: 'R1-UX-QA-SKU' }).locator('input[type="checkbox"]').check()
  await expect(editor.locator('.quote-line-row')).toHaveCount(1)

  const layouts = []
  for (const width of [1440, 1024, 390, 320]) {
    await page.setViewportSize({ width, height: 900 })
    if (width <= 980) {
      await expect.poll(() => page.locator('.sidebar').evaluate(node => node.getBoundingClientRect().right), { timeout: 2_000 })
        .toBeLessThanOrEqual(0)
    }
    await page.evaluate(async () => {
      await document.fonts.ready
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
    })
    const footer = editor.locator('.quote-editor-actions')
    await footer.scrollIntoViewIfNeeded()
    const measurements = await footer.evaluate(node => {
      const footerRect = node.getBoundingClientRect()
      const actions = [...node.querySelectorAll('button')].map(button => {
        const rect = button.getBoundingClientRect()
        return {
          className: [...button.classList].find(name => name.startsWith('quote-action-')),
          text: button.innerText.replace(/\s+/g, ' ').trim(),
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
          right: rect.right,
          visible: rect.width > 0 && rect.height > 0,
          textFits: button.scrollWidth <= button.clientWidth + 1,
        }
      })
      return {
        viewport: innerWidth,
        sidebar: (() => {
          const node = document.querySelector('.sidebar')
          const rect = node?.getBoundingClientRect()
          const menu = document.querySelector('.mobile-menu')
          return {
            open: node?.classList.contains('open') || false,
            x: rect?.x ?? null,
            right: rect?.right ?? null,
            transform: node ? getComputedStyle(node).transform : null,
            mobileMenuVisible: Boolean(menu && getComputedStyle(menu).display !== 'none'),
            scrimVisible: Boolean(document.querySelector('.scrim')),
          }
        })(),
        footer: { x: footerRect.x, right: footerRect.right, width: footerRect.width, scrollWidth: node.scrollWidth, clientWidth: node.clientWidth },
        actions,
      }
    })
    expect(measurements.actions.map(action => action.className)).toEqual([
      'quote-action-cancel', 'quote-action-preview', 'quote-action-save', 'quote-action-save-export',
    ])
    for (const action of measurements.actions) {
      expect(action.visible, `${width}px ${action.className} is visible`).toBe(true)
      expect(action.textFits, `${width}px ${action.className} text fits`).toBe(true)
      expect(action.right).toBeLessThanOrEqual(measurements.footer.right + 1)
    }
    if (width <= 980) expect(measurements.sidebar.right).toBeLessThanOrEqual(0)
    expect(measurements.footer.scrollWidth).toBeLessThanOrEqual(measurements.footer.clientWidth + 1)
    if (width <= 390) {
      expect(measurements.actions.find(action => action.className === 'quote-action-save').width).toBeGreaterThan(measurements.footer.width * 0.75)
      expect(measurements.actions.find(action => action.className === 'quote-action-save-export').width).toBeGreaterThan(measurements.footer.width * 0.75)
      expect(Math.abs(measurements.actions[0].y - measurements.actions[1].y)).toBeLessThanOrEqual(2)
      expect(measurements.actions[2].y).toBeGreaterThan(measurements.actions[1].y)
      expect(measurements.actions[3].y).toBeGreaterThan(measurements.actions[2].y)
    }
    layouts.push(measurements)
    await page.screenshot({ path: path.join(evidenceDir, `chrome-quote-actions-${width}.png`), timeout: 15_000 })
  }

  // Preview opens from the current draft and closing it preserves the selected line.
  await editor.getByRole('button', { name: '预览报价单', exact: true }).click()
  const preview = page.getByRole('dialog', { name: 'PI 预览' })
  await expect(preview).toBeVisible()
  await expect(preview).toContainText('当前内容尚未保存')
  await preview.getByRole('button', { name: '关闭预览', exact: true }).click()
  await expect(editor.locator('.quote-line-row')).toHaveCount(1)

  // Save-only creates a quote without starting an export.
  const saveResponsePromise = page.waitForResponse(response =>
    new URL(response.url()).pathname === '/api/quotes/' && response.request().method() === 'POST')
  await editor.getByRole('button', { name: '保存报价', exact: true }).click()
  const saveResponse = await saveResponsePromise
  expect(saveResponse.status()).toBe(201)
  const savedQuote = await saveResponse.json()
  await expect(editor).toHaveCount(0)

  // Save-and-export remains a single action: create succeeds and an XLSX download follows.
  editor = await openEditor()
  await editor.locator('.sku-picker-options label').filter({ hasText: 'R1-UX-QA-SKU' }).locator('input[type="checkbox"]').check()
  const exportResponsePromise = page.waitForResponse(response =>
    new URL(response.url()).pathname === '/api/quotes/' && response.request().method() === 'POST')
  const downloadPromise = page.waitForEvent('download')
  await editor.getByRole('button', { name: '保存并导出 Excel', exact: true }).click()
  const exportResponse = await exportResponsePromise
  expect(exportResponse.status()).toBe(201)
  const exportedQuote = await exportResponse.json()
  const risk = page.getByRole('dialog', { name: '导出前风险提示' })
  await expect(risk).toBeVisible()
  await risk.getByRole('button', { name: '了解风险，继续导出' }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename().toLowerCase()).toContain('.xlsx')
  const downloadPath = path.join(process.env.ISOLATED_TEST_ROOT, download.suggestedFilename())
  await download.saveAs(downloadPath)
  const downloadBytes = (await fs.stat(downloadPath)).size
  expect(downloadBytes).toBeGreaterThan(0)
  expect(apiResponses.some(response => response.method === 'GET' && response.path === `/api/quotes/${exportedQuote.id}/export/` && response.status === 200)).toBe(true)
  await fs.copyFile(downloadPath, path.join(evidenceDir, 'downloaded-quote.xlsx'))
  await expect(editor).toHaveCount(0)

  await fs.writeFile(path.join(evidenceDir, 'browser-results.json'), JSON.stringify({
    browser: await page.evaluate(() => navigator.userAgent),
    browserVersion: context.browser()?.version() || null,
    layouts,
    preview: 'opened and closed; draft line remained',
    save: { status: saveResponse.status(), id: savedQuote.id, quote_no: savedQuote.quote_no },
    saveAndExport: { status: exportResponse.status(), id: exportedQuote.id, quote_no: exportedQuote.quote_no, filename: download.suggestedFilename(), downloadBytes },
    apiResponses,
  }, null, 2), 'utf8')
  } catch (error) {
    failureMessage = String(error?.message || error)
    throw error
  } finally {
    let downloadFailure = null
    if (observedDownload && failureMessage) {
      downloadFailure = await Promise.race([
        observedDownload.failure().catch(error => String(error)),
        new Promise(resolve => setTimeout(() => resolve('download failure status unavailable'), 2_000)),
      ])
    }
    emit('test-finish', {
      status: failureMessage ? 'failed' : 'in-progress', failureMessage, pageClosed: page.isClosed(), contextClosed,
      pageUrl: page.isClosed() ? null : page.url(),
      downloadStarted: Boolean(observedDownload), downloadFailure,
      suggestedFilename: observedDownload?.suggestedFilename() || null,
      downloadDirectory: process.env.ISOLATED_TEST_ROOT || null,
      evidenceDir, outputDir: testInfo.outputDir, apiResponses,
    })
  }
})
