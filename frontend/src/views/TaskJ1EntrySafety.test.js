import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = async path => readFile(new URL(path, import.meta.url), 'utf8')

test('dashboard customer and follow-up rows use the existing detail query mode', async () => {
  const view = await source('./Dashboard.vue')
  assert.match(view, /path: '\/customers', query: \{ detail: c\.id \}/)
  assert.match(view, /path: '\/follow-ups', query: \{ detail: f\.id \}/)
  assert.match(view, /商品分类销售额（仅商品行）/)
})

test('finance due contracts navigate by their returned record IDs', async () => {
  const view = await source('./FinanceDashboardPage.vue')
  const purchaseView = await source('./PurchaseOrderPage.vue')
  assert.match(view, /row\.order \? '\/orders' : '\/purchase-orders'/)
  assert.match(view, /detail: row\.order \|\| row\.purchase_order/)
  assert.match(purchaseView, /route\.query\.detail/)
  assert.match(purchaseView, /expandedId\.value = Number\(route\.query\.detail\)/)
})

test('import page exposes only supported types and explains insert-only finance imports', async () => {
  const view = await source('./ImportPage.vue')
  assert.match(view, /const types = \{ customers:/)
  assert.doesNotMatch(view, /orders:\s*\[/)
  assert.match(view, /财务流水只新增/)
  assert.match(view, /正式订单导入暂未开放/)
  assert.doesNotMatch(view, /订单使用 <code>order_no<\/code>/)
})

test('top bar has no fake search or notification controls and uses current operator initials', async () => {
  const view = await source('../App.vue')
  assert.doesNotMatch(view, /quick-search|<Bell\b|<Search\b/)
  assert.match(view, /:title="operator\.name">\{\{ operatorInitial \}\}/)
  assert.doesNotMatch(view, /<div class="avatar">J<\/div>/)
})
