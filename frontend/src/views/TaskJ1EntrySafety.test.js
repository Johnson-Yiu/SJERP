import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = async path => readFile(new URL(path, import.meta.url), 'utf8')

test('dashboard due follow-ups preserve current-due context when opening the list or a record', async () => {
  const view = await source('./Dashboard.vue')
  assert.match(view, /path: '\/customers', query: \{ detail: c\.id \}/)
  assert.match(view, /RouterLink to="\/follow-ups\?due=true">查看全部/)
  assert.match(view, /path: '\/follow-ups', query: \{ due: 'true', detail: f\.id \}/)
  assert.match(view, /商品分类销售额（仅商品行）/)
})

test('finance due contracts navigate by their returned record IDs', async () => {
  const view = await source('./FinanceDashboardPage.vue')
  const purchaseView = await source('./PurchaseOrderPage.vue')
  assert.match(view, /row\.order \? '\/orders' : '\/purchase-orders'/)
  assert.match(view, /detail: row\.order \|\| row\.purchase_order/)
  assert.match(purchaseView, /route\.query\.detail/)
  assert.match(purchaseView, /parseDocumentDetailId\(route\.query\.detail\)/)
})

test('import page exposes only supported types and explains insert-only finance imports', async () => {
  const view = await source('./ImportPage.vue')
  assert.match(view, /const types = \{ customers:/)
  assert.doesNotMatch(view, /orders:\s*\[/)
  assert.match(view, /财务流水只新增/)
  assert.match(view, /正式订单导入暂未开放/)
  assert.doesNotMatch(view, /订单使用 <code>order_no<\/code>/)
})

test('import page uses preview and explicit confirmation before a write', async () => {
  const view = await source('./ImportPage.vue')
  assert.match(view, /\/import\/csv\/preview\//)
  assert.match(view, /\/import\/csv\/execute\//)
  assert.match(view, /confirmDialog\(\{ title: '确认执行导入'/)
  assert.match(view, /预览并校验/)
  assert.match(view, /确认执行导入/)
  assert.match(view, /校验未通过，不会写入任何数据。/)
  assert.match(view, /下载失败清单 CSV/)
})

test('top bar has no fake search or notification controls and uses current operator initials', async () => {
  const view = await source('../App.vue')
  assert.doesNotMatch(view, /quick-search|<Bell\b|<Search\b/)
  assert.match(view, /:title="operator\.name">\{\{ operatorInitial \}\}/)
  assert.doesNotMatch(view, /<div class="avatar">J<\/div>/)
})
