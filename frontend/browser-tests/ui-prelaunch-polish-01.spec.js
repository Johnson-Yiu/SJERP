import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

test.beforeEach(({ browserName }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== 'ui-prelaunch-polish-01.spec.js',
    'Run this suite with the dedicated authenticated Chrome isolation profile.')
  expect(browserName).toBe('chromium')
})

test.setTimeout(120000)
for (const [width, height] of [[1366, 768], [1920, 1080]]) {
test('order deletion locks the row until a failed request can be retried ' + width, async ({ page, browser }, testInfo) => {
  const unique = `${width}-${Date.now()}`
  const customerResponse = await post(page, '/api/customers/', {data:{code:'UI-'+unique,name:'合成删除客户'+unique,country:'CN',contacts:[{name:'合成联系人',email:'synthetic@example.test'}]}})
  expect(customerResponse.status()).toBe(201)
  const customer = await customerResponse.json()
  const categoryResponse = await post(page, '/api/categories/', {data:{name:'合成删除分类'+unique}})
  expect(categoryResponse.status()).toBe(201)
  const category = await categoryResponse.json()
  const productResponse = await post(page, '/api/products/', {data:{code:'UI'+unique,name:'合成删除产品'+unique,category:category.id,sales_model_prefix:'DEL'+width}})
  expect(productResponse.status()).toBe(201)
  const product = await productResponse.json()
  const skuResponse = await post(page, '/api/skus/', {data:{sku:'DEL'+unique,product:product.id,unit:'pcs',sales_model:'DEL'+width}})
  expect(skuResponse.status()).toBe(201)
  const sku = await skuResponse.json()
  const orderResponse = await post(page, '/api/orders/', {data:{customer:customer.id,order_date:'2026-11-14',currency:'CNY',exchange_rate:'1',items:[{sku:sku.id,quantity:'1',unit_price:'10'}]}})
  expect(orderResponse.status(),await orderResponse.text()).toBe(201)
  const order = await orderResponse.json()
  const id = order.id
  const number = order.order_no
  await page.setViewportSize({ width, height })
  await page.goto('/orders?search=' + number)
  const remove = page.getByRole('button', { name: '删除 ' + number })
  const confirm = page.getByTestId('dialog-confirm')
  let requests = 0
  let release
  const blocked = new Promise(resolve => { release = resolve })
  await page.route('**/api/orders/' + id + '/', async route => {
    if (route.request().method() !== 'DELETE') return route.continue()
    if (++requests !== 1) return route.continue()
    await blocked
    await route.fulfill({ status: 503, json: { detail: '合成故障' } })
  })
  await remove.dblclick()
  await confirm.click()
  await expect.poll(() => requests).toBe(1)
  await expect(remove).toBeDisabled()
  const box = await remove.boundingBox()
  expect(box.y + box.height).toBeLessThan(height)
  expect(box.x + box.width).toBeLessThanOrEqual(width)
  await page.mouse.dblclick(box.x + box.width / 2, box.y + box.height / 2)
  expect(requests).toBe(1)
  const screenshot = await page.screenshot({ path: testInfo.outputPath(`delete-pending-${width}.png`) })
  release()
  await expect(remove).toBeEnabled()
  expect((await page.request.get('/api/orders/' + id + '/')).ok()).toBe(true)
  await remove.click()
  await confirm.click()
  await expect(remove).toHaveCount(0)
  expect(requests).toBe(2)
  expect((await page.request.get('/api/orders/' + id + '/')).status()).toBe(404)
  await writeFile(testInfo.outputPath('delete.json'), JSON.stringify({
    browser: browser.version(), id, requests, width, height,
    screenshotSha256: createHash('sha256').update(screenshot).digest('hex'),
  }, null, 2))
})

test('first bank-event load displays progress and supports retry ' + width, async ({ page, browser }, testInfo) => {
  if (width === 1366) {
    execFileSync(process.env.ISOLATED_TEST_PYTHON, [fileURLToPath(new URL('../../docs/uat-evidence/ui-final-state-closeout-03/seed.py', import.meta.url))], {
      cwd: fileURLToPath(new URL('../../backend/', import.meta.url)), encoding: 'utf8', env: { ...process.env, CLOSEOUT_FINANCE_LAYOUT: '1' },
    })
  }
  let release
  const wait = new Promise(resolve => { release = resolve })
  let requests = 0
  await page.route('**/api/rmb-cash-events/**', async route => {
    if (++requests > 6) return route.continue()
    await wait
    await route.fulfill({ status: 503, json: { detail: '合成故障' } })
  })
  await page.setViewportSize({ width, height })
  await page.goto('/rmb-cash-events')
  await expect(page.getByText('正在加载…', { exact: true })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath(`bank-events-loading-${width}.png`) })
  release()
  const retry = page.getByRole('button', { name: '重试', exact: true })
  await expect(retry).toBeVisible({ timeout: 12000 })
  await page.screenshot({ path: testInfo.outputPath(`bank-events-error-${width}.png`) })
  await retry.click()
  await expect(page.getByText('正在加载…', { exact: true })).toBeHidden()
  await expect(page.getByText('合成故障', { exact: true })).toBeHidden()
  expect(requests).toBe(7)
  const row = page.getByRole('row').filter({ hasText: 'EVID-BANK-CLOSEOUT' })
  await expect(row).toBeVisible()
  await row.getByRole('button', { name: /详情/ }).click()
  const dialog = page.getByRole('dialog', { name: 'EVID-BANK-CLOSEOUT' })
  await expect(dialog).toBeVisible()
  const close = dialog.getByRole('button', { name: /关闭/ }).first()
  const bounds = await close.boundingBox()
  expect(bounds.y).toBeGreaterThanOrEqual(0)
  expect(bounds.y + bounds.height).toBeLessThanOrEqual(height)
  await page.screenshot({ path: testInfo.outputPath(`bank-detail-${width}.png`) })
  await close.click()
  await expect(dialog).toBeHidden()
  await writeFile(testInfo.outputPath('bank.json'), JSON.stringify({ source: execFileSync('git', ['rev-parse','HEAD'], {encoding:'utf8'}).trim(), browser: browser.version(), width, height, requests, nonempty: true, detailClosed: true, metrics: await page.evaluate(() => ({dpr:devicePixelRatio,width:innerWidth,height:innerHeight})) }, null, 2))
  await page.screenshot({ path: testInfo.outputPath(`bank-events-recovered-${width}.png`) })
})

}

async function post(page,url,options) {
 const token=(await page.context().cookies()).find(c=>c.name==='csrftoken')?.value
 return page.request.post(url,{...options,headers:{...options?.headers,'X-CSRFToken':token}})
}
