import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import {
  documentDetailState,
  parseDocumentDetailId,
  withDocumentDetailQuery,
  withoutDocumentDetailQuery,
} from '../utils/documentDetailRoute.js'

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

test('quote list export uses one consolidated SKU risk notice before downloading', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /api\.get\('\/quotes\/risk-preview\//)
  assert.match(source, /quoteRiskRows\.value = .*filter\(item => item\.has_risk\)/)
  assert.match(source, /quoteRiskCheckUnavailable\.value = true/)
  assert.match(source, /:risk-check-unavailable="quoteRiskCheckUnavailable"/)
  assert.match(source, /<QuoteRiskNotice v-if="quoteRiskOpen"/)
})

test('quote list provides summary metrics, filters, and newest-first sorting', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /const quoteMetrics = computed/)
  assert.match(source, /quoteStatusFilter = computed/)
  assert.match(source, /quoteSort = computed/)
  assert.match(source, /ordering: quoteSort\.value/)
  assert.match(source, /status: quoteStatusFilter\.value/)
})

test('every quote row opens detail and dedicated expansion stops propagation', async () => {
  const source = await readFile(componentUrl, 'utf8')
  assert.match(source, /function activateQuoteTreeRow\(row\) \{ openDetail\(row\) \}/)
  assert.match(source, /@click\.stop="toggleQuoteNode\(row.id\)"/)
  assert.doesNotMatch(source, /acceptedAmount|已接受金额/)
})

test('orders reuse the compact summary cards used by the quotation desk', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /import SummaryCards from '\.\.\/components\/SummaryCards\.vue'/)
  assert.match(source, /const orderMetrics = computed/)
  assert.match(source, /<SummaryCards v-if="isOrder && hasLoaded" :items="orderMetrics"/)
})

test('order editor does not expose manual lifecycle status changes', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /<input value="草稿" readonly/)
  assert.match(source, /保存为草稿，确认后开始履约/)
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

test('order draft edits use PUT, close and refresh on success, and surface failed saves', async () => {
  const source = await readFile(componentUrl, 'utf8')
  const save = source.slice(source.indexOf('async function save()'), source.indexOf('async function handleQuoteSaved'))

  assert.match(save, /delete data\.status; delete data\.order_no/)
  assert.match(save, /api\.put\(`\/\$\{props\.type\}\/\$\{editingId\.value\}\/`, data\)/)
  assert.match(save, /open\.value = false\s+notify\('单据已保存'\)\s+await clearModalRoute\(router, route\)\s+await load\(\)/)
  assert.match(save, /catch \(e\) \{ notify\(e\.message, true\) \}/)
})

test('order editor reports an invalid non-positive line quantity before sending a request', async () => {
  const source = await readFile(componentUrl, 'utf8')
  const save = source.slice(source.indexOf('async function save()'), source.indexOf('async function handleQuoteSaved'))

  assert.match(source, /<form class="modal wide" novalidate @submit\.prevent="save">/)
  assert.match(save, /form\.items\.some\(i => Number\(i\.quantity\) <= 0\)/)
  assert.match(save, /每条 SKU 明细的数量必须大于 0。/)
})

test('order list limits edit and delete operations to drafts', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /v-if="can\('orders', 'update'\) && row\.status === 'draft'" class="mini-btn" :aria-label="`编辑/)
  assert.match(source, /v-if="can\('orders', 'delete'\) && row\.status === 'draft'" class="mini-btn" :aria-label="`删除/)
})

test('editing from the order workbench reloads the current order before opening the editor', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /async function editRelatedOrder\(\)/)
  assert.match(source, /await api\.get\(`\/orders\/\$\{orderDetailId\.value\}\/`\)/)
  assert.match(source, /await edit\(row, \{ closeDetail: false \}\)/)
})

test('document deep links initialize and dynamically synchronize quote and order details', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.deepEqual(documentDetailState('orders', '4'), { quoteDetailId: null, orderDetailId: 4 })
  assert.deepEqual(documentDetailState('quotes', '10'), { quoteDetailId: 10, orderDetailId: null })
  assert.deepEqual(documentDetailState('orders', '5'), { quoteDetailId: null, orderDetailId: 5 })
  assert.deepEqual(documentDetailState('orders', undefined), { quoteDetailId: null, orderDetailId: null })
  assert.match(source, /watch\(\[\(\) => props\.type, \(\) => route\.query\.detail\], syncDetailFromRoute, \{ immediate: true \}\)/)
})

test('closing a document detail removes only detail and preserves remaining route state', async () => {
  const route = {
    path: '/orders',
    query: { detail: '4', search: 'SO-4', customer: '7', status: 'confirmed', create: '1' },
    hash: '#payments',
  }
  const source = await readFile(componentUrl, 'utf8')

  assert.deepEqual(withoutDocumentDetailQuery(route), {
    path: '/orders',
    query: { search: 'SO-4', customer: '7', status: 'confirmed', create: '1' },
    hash: '#payments',
  })
  assert.match(source, /router\.replace\(workbenchCloseLocation\(route\)\)/)
  assert.match(source, /@close="closeDocumentDetail"/)
})

test('opening list rows pushes their detail id into the current route for refresh and history', async () => {
  const route = { path: '/orders', query: { search: 'SO', customer: '7', sku: '12' }, hash: '#items' }
  const source = await readFile(componentUrl, 'utf8')

  assert.deepEqual(withDocumentDetailQuery(route, 4), {
    path: '/orders',
    query: { search: 'SO', customer: '7', sku: '12', detail: '4', tab: 'overview' },
    hash: '#items',
  })
  assert.match(source, /function openDetail\(row\) \{ void router\.push\(withDocumentDetailQuery\(route, row\.id\)\) \}/)
  assert.match(source, /orderDetailLocation\(id, 'overview', route\.fullPath\)/)
  assert.match(source, /quoteDetailLocation\(id, 'overview', route\.fullPath\)/)
})

test('invalid document ids cannot break the list route and large not-found ids remain loadable as details', () => {
  assert.equal(parseDocumentDetailId('999999999'), 999999999)
  for (const value of ['0', '-4', 'not-an-id', 'NaN', 'undefined', 'null', Number.MAX_SAFE_INTEGER + 1, ['4', '5']]) {
    assert.equal(parseDocumentDetailId(value), null)
  }
  assert.deepEqual(documentDetailState('orders', 'not-an-id'), { quoteDetailId: null, orderDetailId: null })
})
