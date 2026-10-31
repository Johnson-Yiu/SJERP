import { expect, test } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'

const evidenceDir = path.resolve(process.env.R1_UX_QUOTE_ACTIONS_EVIDENCE_DIR || '')
if (!process.env.R1_UX_QUOTE_ACTIONS_EVIDENCE_DIR) {
  throw new Error('R1_UX_QUOTE_ACTIONS_EVIDENCE_DIR must point to the task evidence directory.')
}

test('quote editor actions stay readable at desktop and narrow widths and preserve preview/save/export', async ({ page }) => {
  await fs.mkdir(evidenceDir, { recursive: true })
  const fixture = JSON.parse(await fs.readFile(path.join(evidenceDir, 'fixture.json'), 'utf8'))
  expect(fixture.synthetic_only).toBe(true)
  const apiResponses = []
  page.on('response', response => {
    if (new URL(response.url()).pathname.startsWith('/api/quotes/')) {
      apiResponses.push({ method: response.request().method(), path: new URL(response.url()).pathname, status: response.status() })
    }
  })

  async function openEditor() {
    await page.goto(`/quotes?create=1&customer=${fixture.customer}`)
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
    expect(measurements.footer.scrollWidth).toBeLessThanOrEqual(measurements.footer.clientWidth + 1)
    if (width <= 390) {
      expect(measurements.actions.find(action => action.className === 'quote-action-save').width).toBeGreaterThan(measurements.footer.width * 0.75)
      expect(measurements.actions.find(action => action.className === 'quote-action-save-export').width).toBeGreaterThan(measurements.footer.width * 0.75)
      expect(Math.abs(measurements.actions[0].y - measurements.actions[1].y)).toBeLessThanOrEqual(2)
      expect(measurements.actions[2].y).toBeGreaterThan(measurements.actions[1].y)
      expect(measurements.actions[3].y).toBeGreaterThan(measurements.actions[2].y)
    }
    layouts.push(measurements)
    await page.screenshot({ path: path.join(evidenceDir, `chrome-quote-actions-${width}.png`) })
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
  const download = await downloadPromise
  expect(download.suggestedFilename().toLowerCase()).toContain('.xlsx')
  const downloadPath = path.join(process.env.ISOLATED_TEST_ROOT, download.suggestedFilename())
  await download.saveAs(downloadPath)
  const downloadBytes = (await fs.stat(downloadPath)).size
  await expect(editor).toHaveCount(0)

  await fs.writeFile(path.join(evidenceDir, 'browser-results.json'), JSON.stringify({
    browser: await page.evaluate(() => navigator.userAgent),
    layouts,
    preview: 'opened and closed; draft line remained',
    save: { status: saveResponse.status(), id: savedQuote.id, quote_no: savedQuote.quote_no },
    saveAndExport: { status: exportResponse.status(), id: exportedQuote.id, quote_no: exportedQuote.quote_no, filename: download.suggestedFilename(), downloadBytes },
    apiResponses,
  }, null, 2), 'utf8')
})
