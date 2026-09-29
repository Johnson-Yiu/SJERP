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
