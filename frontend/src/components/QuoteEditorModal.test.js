import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./QuoteEditorModal.vue', import.meta.url)

test('SKU picker synchronizes multi-selection into quote line items', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /const selectedSkuIds = computed/)
  assert.match(source, /function syncSelectedSkus\(ids\)/)
  assert.match(source, /class="sku-selection-panel"/)
  assert.match(source, /v-model="selectedSkuIds"/)
  assert.doesNotMatch(source, /添加一行/)
})

test('SKU picker keeps a fixed height while search results scroll', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /\.sku-selection-panel\{[^}]*height:268px/)
  assert.match(source, /\.sku-picker-list\{display:flex;flex-direction:column/)
  assert.match(source, /\.sku-picker-options\{flex:1 1 auto;min-height:0;overflow:auto/)
})

test('quote editor lets users save without exporting the Excel file', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /async function save\(shouldExport = false\)/)
  assert.match(source, /if \(!shouldExport\) \{ emit\('close'\); return \}/)
  assert.match(source, /@click="save\(false\)"/)
  assert.match(source, /保存报价/)
  assert.match(source, /@click="save\(true\)"/)
  assert.match(source, /保存并导出 Excel/)
})

test('quote editor blocks a validity date earlier than the quote date', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /draft\.valid_until < draft\.quote_date/)
  assert.match(source, /有效期不能早于报价日期。/)
})

test('quote status is read-only and cannot be selected while creating or revising', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /label>状态<\/label><input value="草稿" readonly/)
  assert.doesNotMatch(source, /<select[^>]*v-model="draft\.status"/)
  assert.doesNotMatch(source, /<option[^>]*value="(?:accepted|rejected|expired)"/)
  assert.match(source, /mode === 'revise' \? '创建报价修订版'/)
})

test('quote export shows one consolidated risk notice after the quote is saved', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /api\.get\('\/quotes\/risk-preview\//)
  assert.match(source, /riskRows\.value\.length\) \{ riskNoticeOpen\.value = true/)
  assert.match(source, /<QuoteRiskNotice v-if="riskNoticeOpen"/)
})
