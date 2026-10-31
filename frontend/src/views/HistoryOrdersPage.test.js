import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./HistoryOrdersPage.vue', import.meta.url)
const accessControlUrl = new URL('../accessControl.js', import.meta.url)
const routerUrl = new URL('../router.js', import.meta.url)

test('history order entry uses isolated endpoints and keeps the analysis-only label visible', async () => {
  const source = await readFile(componentUrl, 'utf8')
  assert.match(source, /\/orders\/historical\//)
  assert.match(source, /\/purchase-orders\/historical\//)
  assert.match(source, /历史订单 · 仅用于经营分析/)
  assert.match(source, /不生成应收、应付、采购或库存记录/)
})

test('history order entry preserves the supplied historical date and does not expose formal actions', async () => {
  const source = await readFile(componentUrl, 'utf8')
  assert.match(source, /真实订单日期/)
  assert.match(source, /order_date: ''/)
  assert.doesNotMatch(source, /confirm_order|generate-purchase-drafts|payment-plans|ship\//)
})

test('history page keeps unauthorized optional requests from blanking authorized data', async () => {
  const source = await readFile(componentUrl, 'utf8')
  assert.match(source, /loadOptional\(/)
  assert.match(source, /canSalesView/)
  assert.match(source, /canPurchaseView/)
  assert.match(source, /availableTabs/)
  assert.match(source, /当前账号没有历史订单查看权限/)
  assert.match(source, /当前账号没有完整的/)
})

test('history page does not offer an entry form without its master-data permissions', async () => {
  const source = await readFile(componentUrl, 'utf8')
  assert.match(source, /can\('customers', 'view'\)/)
  assert.match(source, /can\('suppliers', 'view'\)/)
  assert.match(source, /can\('skus', 'view'\)/)
  assert.match(source, /v-if="canCurrentEntry"/)
  assert.match(source, /max-width:700px/)
})

test('history navigation accepts either sales or purchasing view permission', async () => {
  const accessControl = await readFile(accessControlUrl, 'utf8')
  const router = await readFile(routerUrl, 'utf8')
  assert.match(accessControl, /canAccessHistoricalOrders/)
  assert.match(accessControl, /can\('orders', 'view'\) \|\| can\('purchases', 'view'\)/)
  assert.match(router, /to\.path === '\/historical-orders'/)
  assert.match(router, /canAccessHistoricalOrders\(\)/)
})

test('history analysis renders permission-filtered detail tables with local narrow-screen scrolling', async () => {
  const source = await readFile(componentUrl, 'utf8')
  assert.match(source, /analysisSections/)
  assert.match(source, /by_customer/)
  assert.match(source, /by_country/)
  assert.match(source, /by_sku/)
  assert.match(source, /by_category/)
  assert.match(source, /by_supplier/)
  assert.match(source, /analysis-table-wrap/)
  assert.match(source, /overflow-x:auto/)
  assert.match(source, /当前权限下暂无可展示的历史明细/)
})
