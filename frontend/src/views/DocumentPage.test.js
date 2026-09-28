import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./DocumentPage.vue', import.meta.url)

test('quote list renders a recursive parent-child tree with classified document icons', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /const quoteTreeRows = computed/)
  assert.match(source, /function toggleQuoteNode\(quoteId\)/)
  assert.match(source, /row\.parent_quote/)
  assert.match(source, /FolderOpen/)
  assert.match(source, /FileText/)
  assert.match(source, /--tree-depth/)
})

test('quote tree actions preserve detail, edit, and Excel export entry points', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /@click\.stop="openDetail\(row\)"/)
  assert.match(source, /@click\.stop="edit\(row\)"/)
  assert.match(source, /@click\.stop="exportQuote\(row\)"/)
})

test('quote list provides summary metrics, filters, and newest-first sorting', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /const quoteMetrics = computed/)
  assert.match(source, /quoteStatusFilter = ref\(''\)/)
  assert.match(source, /quoteSort = ref\('-updated_at'\)/)
  assert.match(source, /ordering: quoteSort\.value/)
  assert.match(source, /status: quoteStatusFilter\.value/)
})

test('clicking a root quote only expands revisions and never opens quote details', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /function activateQuoteTreeRow\(row\)/)
  assert.match(source, /if \(row\.isRoot\) \{\s*if \(row\.hasChildren\) toggleQuoteNode\(row\.id\)\s*return/s)
  assert.match(source, /\}\s*openDetail\(row\)/s)
})

test('orders reuse the compact summary cards used by the quotation desk', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /import SummaryCards from '\.\.\/components\/SummaryCards\.vue'/)
  assert.match(source, /const orderMetrics = computed/)
  assert.match(source, /<SummaryCards v-if="isOrder" :items="orderMetrics"/)
})

test('order editor does not expose manual lifecycle status changes', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /草稿（确认后进入正式履约）/)
  assert.match(source, /订单状态由确认、生产、发货、完成或取消等业务动作推进/)
  assert.match(source, /delete data\.status; delete data\.order_no/)
  assert.doesNotMatch(source, /editableOrderStatuses/)
})

test('order creation leaves number generation to the backend and keeps saved numbers read-only', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.doesNotMatch(source, /Date\.now\(\)/)
  assert.match(source, /保存后由系统自动生成/)
  assert.match(source, /delete data\.order_no/)
  assert.match(source, /class="readonly-input" readonly/)
})

test('order list limits edit and delete operations to drafts', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /v-if="row\.status === 'draft'" class="mini-btn" :aria-label="`编辑/)
  assert.match(source, /v-if="row\.status === 'draft'" class="mini-btn" :aria-label="`删除/)
})

test('editing from the order workbench reloads the current order before opening the editor', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /async function editRelatedOrder\(\)/)
  assert.match(source, /await api\.get\(`\/orders\/\$\{orderDetailId\.value\}\/`\)/)
  assert.match(source, /await edit\(row, \{ closeDetail: false \}\)/)
})
