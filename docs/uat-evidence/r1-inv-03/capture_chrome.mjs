import path from 'node:path'
import { createRequire } from 'node:module'

const require = createRequire(new URL('../../../frontend/package.json', import.meta.url))
const { chromium } = require('playwright')

const baseUrl = 'http://127.0.0.1:5195/purchase-orders?create=1'
const outputDir = path.resolve(process.cwd(), '..', 'docs', 'uat-evidence', 'r1-inv-03')
console.log(`OUTPUT_DIR=${outputDir}`)

const browser = await chromium.launch({
  executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  headless: true,
})

for (const [width, height] of [[1440, 900], [1024, 900], [700, 900]]) {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 })
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  await page.getByRole('combobox', { name: '供应商' }).selectOption({ label: '库存参考验收供应商' })
  await page.getByRole('checkbox', { name: /INV3-STOCKED-001/ }).check()
  await page.getByText('实际库存', { exact: true }).waitFor({ state: 'visible', timeout: 5000 })
  await page.screenshot({ path: path.join(outputDir, `purchase-reference-${width}.png`), fullPage: false })
  await page.close()
}

await browser.close()
console.log('CHROME_SCREENSHOTS=1440,1024,700')
