import { chromium } from 'playwright'
import fs from 'node:fs/promises'
import path from 'node:path'

const base = 'http://127.0.0.1:5191'
const routes = ['/', '/reports', '/customers', '/contacts', '/follow-ups', '/quotes', '/orders', '/suppliers', '/purchase-orders', '/products', '/categories', '/skus', '/sku-packaging', '/inventory', '/transactions', '/finance', '/receivables', '/payables', '/hs-codes', '/import', '/organization']
const output = 'C:/Users/Johnson/.codex/visualizations/2026/09/14/01a0a03d-8d8f-7241-a788-3b8d857d5f1a/typography-qa'
await fs.mkdir(output, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const results = []
for (const viewport of [{ name: 'desktop', width: 1440, height: 900 }, { name: 'mobile', width: 390, height: 844 }]) {
  const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1 })
  for (const route of routes) {
    const response = await page.goto(`${base}${route}`, { waitUntil: 'networkidle' })
    await page.screenshot({ path: path.join(output, `${viewport.name}-${route === '/' ? 'dashboard' : route.slice(1)}.png`), fullPage: false })
    const inspection = await page.evaluate(() => {
      const root = document.documentElement
      const measured = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6,p,small,button,input,select,textarea,th,td')]
        .filter(element => getComputedStyle(element).display !== 'none')
        .map(element => ({ tag: element.tagName, size: getComputedStyle(element).fontSize, text: (element.textContent || element.getAttribute('placeholder') || '').trim().slice(0, 40) }))
      const sizes = [...new Set(measured.map(item => item.size))].sort((a, b) => Number.parseFloat(a) - Number.parseFloat(b))
      const overflow = [...document.querySelectorAll('body *')].filter(element => {
        const style = getComputedStyle(element)
        return style.overflowX === 'visible' && element.scrollWidth > element.clientWidth + 2 && element.clientWidth > 0
      }).slice(0, 12).map(element => ({ tag: element.tagName, className: element.className, width: element.clientWidth, scrollWidth: element.scrollWidth }))
      return { title: document.title, bodyWidth: root.scrollWidth, viewportWidth: window.innerWidth, sizes, overflow, headings: measured.filter(item => /^H[1-6]$/.test(item.tag)).slice(0, 8) }
    })
    results.push({ viewport: viewport.name, route, status: response?.status(), ...inspection })
  }
  await page.close()
}
await browser.close()
await fs.writeFile(path.join(output, 'results.json'), JSON.stringify(results, null, 2))
console.log(JSON.stringify(results, null, 2))
