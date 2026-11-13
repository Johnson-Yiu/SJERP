# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: iss037-print-output-acceptance.spec.js >> Chrome UI print to PDF multipage 1440px headers=false
- Location: browser-tests\iss037-print-output-acceptance.spec.js:74:1

# Error details

```
Error: expect(received).not.toHaveLength(expected)

Expected length: not 0
Received array:      []

Call Log:
- Timeout 60000ms exceeded while waiting on the predicate
```

# Test source

```ts
  22  |   const formal = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(fixtureRoot, 'seed_formal_matrix.py')], {
  23  |     cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8',
  24  |   })
  25  |   expect(formal.status, formal.stderr).toBe(0)
  26  |   formalFixture = JSON.parse(formal.stdout.trim().split('\n').at(-1))
  27  | })
  28  | 
  29  | test('saved PI blocks printing when a document image fails', async ({ page }) => {
  30  |   await page.setViewportSize({ width: 1440, height: 900 })
  31  |   await page.goto(`/quotes?detail=${fixture.id}`)
  32  |   const detail = page.getByRole('dialog', { name: '报价工作台' })
  33  |   await expect(detail).toBeVisible()
  34  |   await detail.getByRole('button', { name: '预览 PI' }).first().click()
  35  |   const frame = page.locator('iframe[title="已保存 PI"]')
  36  |   await expect(frame).toBeVisible()
  37  |   await frame.evaluate(el => {
  38  |     el.contentWindow.print = () => { el.dataset.printCalled = 'yes' }
  39  |     const img = el.contentDocument.createElement('img')
  40  |     img.src = '/synthetic-missing-iss037.png'
  41  |     el.contentDocument.body.append(img)
  42  |   })
  43  |   await expect.poll(() => frame.evaluate(el => {
  44  |     const img = el.contentDocument.querySelector('img[src="/synthetic-missing-iss037.png"]')
  45  |     return img.complete && img.naturalWidth === 0
  46  |   })).toBe(true)
  47  |   await page.getByRole('dialog', { name: 'PI 预览' }).getByRole('button', { name: '导出 PI PDF' }).click()
  48  |   await expect(page.getByRole('dialog', { name: 'PI 预览' })).toContainText('图片加载失败')
  49  |   await expect(frame).not.toHaveAttribute('data-print-called', 'yes')
  50  |   await page.screenshot({ path: path.join(evidence, 'rerun-image-failure-1440.png') })
  51  | })
  52  | 
  53  | test('saved PI permits printing after resources load on narrow screen', async ({ page }) => {
  54  |   await page.setViewportSize({ width: 390, height: 844 })
  55  |   await page.goto(`/quotes?detail=${fixture.id}`)
  56  |   const detail = page.getByRole('dialog', { name: '报价工作台' })
  57  |   await expect(detail).toBeVisible()
  58  |   await detail.getByRole('button', { name: '预览 PI' }).first().click()
  59  |   const frame = page.locator('iframe[title="已保存 PI"]')
  60  |   await expect(frame).toBeVisible()
  61  |   await frame.evaluate(el => { el.contentWindow.print = () => { el.dataset.printCalled = 'yes' } })
  62  |   await page.screenshot({ path: path.join(evidence, 'rerun-saved-preview-390.png') })
  63  |   await page.getByRole('dialog', { name: 'PI 预览' }).getByRole('button', { name: '导出 PI PDF' }).click()
  64  |   await expect(frame).toHaveAttribute('data-print-called', 'yes')
  65  |   // Independent Chrome PDF rendering, not the UI print-dialog output.
  66  |   const html = await frame.evaluate(el => el.contentDocument.documentElement.outerHTML)
  67  |   const rendered = await page.context().newPage()
  68  |   await rendered.setContent(html, { waitUntil: 'load' })
  69  |   await rendered.pdf({ path: path.join(evidence, 'rerun-independent-chrome-render.pdf'), format: 'A4', printBackground: true })
  70  |   await rendered.close()
  71  | })
  72  | 
  73  | for (const [label, width, headers = false] of [['complete', 1440], ['complete', 1440, true], ['complete', 390], ['multipage', 1440], ['optional-empty', 1440]]) {
  74  | test(`Chrome UI print to PDF ${label} ${width}px headers=${headers}`, async ({ baseURL }) => {
  75  |   test.setTimeout(150000)
  76  |   const artifactName = `ui-formal-${label}-${width}-headers-${headers}`
  77  |   const sample = formalFixture.samples.find(item => item.label === label)
  78  |   expect(sample.status).toBe('sent')
  79  |   const printRoot = fs.mkdtempSync(path.join(process.env.ISOLATED_TEST_ROOT, 'pi-print-'))
  80  |   const profile = path.join(printRoot, 'profile')
  81  |   const output = path.join(printRoot, 'output')
  82  |   fs.mkdirSync(path.join(profile, 'Default'), { recursive: true })
  83  |   fs.mkdirSync(output, { recursive: true })
  84  |   fs.writeFileSync(path.join(profile, 'Default', 'Preferences'), JSON.stringify({
  85  |     printing: { print_preview_sticky_settings: { appState: JSON.stringify({
  86  |       recentDestinations: [{ id: 'Save as PDF', origin: 'local', account: '' }],
  87  |       selectedDestinationId: 'Save as PDF', version: 2,
  88  |       isHeaderFooterEnabled: headers, isLandscapeEnabled: false, scaling: '100', marginsType: 0,
  89  |       mediaSize: { height_microns: 297000, width_microns: 210000, name: 'ISO_A4', custom_display_name: 'A4' },
  90  |     }) } },
  91  |     savefile: { default_directory: output },
  92  |     download: { default_directory: output, prompt_for_download: false },
  93  |   }))
  94  |   const browser = await chromium.launchPersistentContext(profile, { channel: 'chrome', headless: false, args: ['--kiosk-printing'] })
  95  |   try {
  96  |     const page = await browser.newPage()
  97  |     await page.setViewportSize({ width, height: 900 })
  98  |     await page.goto(`${baseURL}/quotes?detail=${sample.id}`)
  99  |     const detail = page.getByRole('dialog', { name: '报价工作台' })
  100 |     await expect(detail).toBeVisible()
  101 |     const response = page.waitForResponse(r => r.url().includes(`/quotes/${sample.id}/pi-data/`))
  102 |     await detail.getByRole('button', { name: '预览 PI' }).first().click()
  103 |     const pi = await response
  104 |     expect(pi.status()).toBe(200)
  105 |     const saved = await pi.json()
  106 |     expect(saved.seller.name).toBe('Synthetic Seller')
  107 |     expect(saved.buyer.name).toBe(label === 'optional-empty' ? '' : 'Synthetic Recipient')
  108 |     fs.writeFileSync(path.join(evidence, `${artifactName}.json`), JSON.stringify({
  109 |       source: 'UI print button', paper: 'A4', headers, width, quote: sample, api: saved,
  110 |     }, null, 2))
  111 |     await expect(page.locator('iframe[title="已保存 PI"]')).toBeVisible()
  112 |     await page.screenshot({ path: path.join(evidence, `${artifactName}.png`) })
  113 |     // The native print dialog may block the renderer, so schedule a real DOM
  114 |     // click after this evaluation returns and poll the output from Node.
  115 |     await page.evaluate(() => {
  116 |       const button = Array.from(document.querySelectorAll('button')).find(el => el.textContent.includes('导出 PI PDF'))
  117 |       if (!button) throw new Error('PI print button not found')
  118 |       setTimeout(() => button.click(), 100)
  119 |     })
  120 |     // Headed Chrome can finish native PDF output after 20 seconds on a busy
  121 |     // Windows desktop. Keep the real output assertion, with a bounded wait.
> 122 |     await expect.poll(() => fs.readdirSync(output).filter(name => name.endsWith('.pdf')), { timeout: 60000 }).not.toHaveLength(0)
      |                                                                                                                   ^ Error: expect(received).not.toHaveLength(expected)
  123 |     const file = fs.readdirSync(output).find(name => name.endsWith('.pdf'))
  124 |     fs.copyFileSync(path.join(output, file), path.join(evidence, `${artifactName}.pdf`))
  125 |   } finally {
  126 |     await browser.close()
  127 |   }
  128 | })
  129 | }
  130 | 
```