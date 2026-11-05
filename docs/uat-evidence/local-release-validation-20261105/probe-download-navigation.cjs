const http = require('node:http')
const fs = require('node:fs/promises')
const os = require('node:os')
const path = require('node:path')
const { chromium } = require(path.join(process.cwd(), 'node_modules', 'playwright'))

// Mechanism probe only. The zero-filled Blob is not an Excel workbook and this
// cannot establish which navigation events occurred in the failed ERP run.
;(async () => {
  const server = http.createServer((_request, response) => {
    response.writeHead(200, { 'Content-Type': 'text/html' })
    response.end('<button id="run">run</button>')
  })
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'sunjack-quote-blob-probe-'))
  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  const context = await browser.newContext({ acceptDownloads: true })
  const rows = []
  try {
    for (const mode of ['baseline', 'same-document-navigation', 'document-navigation']) {
      const page = await context.newPage()
      const events = []
      page.on('framenavigated', frame => {
        if (frame === page.mainFrame()) events.push({ event: 'navigation', url: frame.url() })
      })
      await page.goto(`http://127.0.0.1:${server.address().port}/`)
      await page.evaluate(caseName => {
        document.querySelector('#run').onclick = () => {
          const url = URL.createObjectURL(new Blob([new Uint8Array(10219)]))
          const anchor = document.createElement('a')
          anchor.href = url
          anchor.download = 'synthetic.xlsx'
          document.body.append(anchor)
          anchor.click()
          if (caseName === 'same-document-navigation') history.pushState({}, '', '/other')
          if (caseName === 'document-navigation') location.assign('/other')
          setTimeout(() => { anchor.remove(); URL.revokeObjectURL(url) }, 1000)
        }
      }, mode)
      const pending = page.waitForEvent('download', { timeout: 15000 })
      await page.locator('#run').click()
      let outcome
      let bytes = null
      try {
        const download = await pending
        const file = path.join(root, `${mode}.xlsx`)
        await download.saveAs(file)
        bytes = (await fs.stat(file)).size
        outcome = await download.failure() || 'saved'
      } catch (error) {
        outcome = String(error.message || error)
      }
      rows.push({ mode, outcome, bytes, events })
      await page.close()
    }
    console.log(JSON.stringify({ browser: browser.version(), root, rows }, null, 2))
  } finally {
    await context.close()
    await browser.close()
    await new Promise(resolve => server.close(resolve))
  }
})().catch(error => { console.error(error); process.exitCode = 1 })
