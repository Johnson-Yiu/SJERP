import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const detailUrl = new URL('./QuoteDetailModal.vue', import.meta.url)
const pageUrl = new URL('../views/DocumentPage.vue', import.meta.url)

test('quote detail exposes only valid status actions for draft and sent quotes', async () => {
  const source = await readFile(detailUrl, 'utf8')

  assert.match(source, /v-if="quote\.status === 'draft' \|\| quote\.status === 'sent'"/)
  assert.match(source, /v-if="quote\.status === 'draft'" class="btn btn-secondary"[^>]*changeStatus\('mark-sent'\)/)
  assert.match(source, /changeStatus\('accept'\)/)
  assert.match(source, /changeStatus\('reject'\)/)
  assert.match(source, /v-if="quote\.status === 'sent'" class="btn btn-secondary"[^>]*changeStatus\('expire'\)/)
})

test('status actions call the API, reload quote workbench, and refresh the quote list', async () => {
  const detail = await readFile(detailUrl, 'utf8')
  const page = await readFile(pageUrl, 'utf8')

  assert.match(detail, /api\.post\(`\/quotes\/\$\{quote\.value\.id\}\/\$\{action\}\/`\)/)
  assert.match(detail, /await load\(\)\s*emit\('status-updated'\)/)
  assert.match(page, /async function handleQuoteStatusUpdated\(\) \{ await load\(\) \}/)
  assert.match(page, /@status-updated="handleQuoteStatusUpdated"/)
  assert.match(detail, /emit\('revise', quote\).*创建修订版/)
  assert.match(page, /aria-label="`创建修订版 \$\{row\.quote_no\}`"/)
  assert.doesNotMatch(page, /aria-label="`编辑 \$\{row\.quote_no\}`"/)
})

test('terminal quote states render no status transition controls', async () => {
  const source = await readFile(detailUrl, 'utf8')

  assert.match(source, /v-if="quote\.status === 'draft' \|\| quote\.status === 'sent'" class="quote-status-actions"/)
  assert.match(source, /quote\.status === 'draft'/)
  assert.match(source, /quote\.status === 'sent'/)
  assert.match(source, /statusSaving/)
})

test('only non-terminal quotes expose the conversion-to-order actions', async () => {
  const source = await readFile(detailUrl, 'utf8')

  assert.match(source, /const canCreateOrder = computed\(\(\) => \['draft', 'sent', 'accepted'\]\.includes\(quote\.value\?\.status\)\)/)
  assert.match(source, /v-if="canCreateOrder" class="btn btn-primary transfer-order"/)
  assert.match(source, /v-if="canCreateOrder" class="btn btn-primary" @click="createOrder"/)
  assert.match(source, /v-if="!canCreateOrder" class="quote-order-unavailable"/)
  assert.match(source, /报价已拒绝或过期，请先创建修订版。/)
})

test('saved and revised PI previews use the currency in the official totals DTO', async () => {
  const detail = await readFile(detailUrl, 'utf8')
  const editor = await readFile(new URL('./QuoteEditorModal.vue', import.meta.url), 'utf8')
  const preview = await readFile(new URL('./QuotePreviewModal.vue', import.meta.url), 'utf8')

  assert.match(detail, /currency: data\.totals\.currency/)
  assert.match(editor, /quote_no: draft\.quote_no,[^\n]*currency: draft\.currency/)
  assert.match(preview, /formatPiAmountWords\(props\.draft\.totals\?\.total_amount, props\.draft\.currency\)/)
})
