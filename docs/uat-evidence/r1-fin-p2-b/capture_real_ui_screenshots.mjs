import playwright from '../../../frontend/node_modules/playwright/index.js'
const { chromium } = playwright

const browser = await chromium.launch({headless: true})
for (const [width, height] of [[1440, 900], [1280, 800], [1024, 768]]) {
  const page = await browser.newPage({viewport: {width, height}})
  await page.goto('http://127.0.0.1:5211/rmb-cash-events', {waitUntil: 'networkidle'})
  await page.screenshot({path: `docs/uat-evidence/r1-fin-p2-b/real-ui-list-${width}.png`, fullPage: true})
  const detail = page.getByRole('button', {name: '查看详情'}).first()
  if (await detail.count()) {
    await detail.click()
    await page.screenshot({path: `docs/uat-evidence/r1-fin-p2-b/real-ui-detail-${width}.png`, fullPage: true})
  }
  await page.close()
}
await browser.close()
