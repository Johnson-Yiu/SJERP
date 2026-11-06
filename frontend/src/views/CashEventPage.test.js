import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const pageUrl = new URL('./CashEventPage.vue', import.meta.url)

test('cash event page keeps the backend two-step and stable-key flow', async () => {
  const source = await readFile(pageUrl, 'utf8')
  for (const endpoint of [
    /api\.get\('\/rmb-cash-events\/'\)/,
    /api\.post\('\/rmb-cash-events\/preview\/'/,
    /api\.get\('\/rmb-cash-events\/sources\/'/,
    /api\.get\('\/rmb-cash-events\/by-request-key\/'/,
    /\/confirm\//,
    /\/cancel\//,
  ]) assert.match(source, endpoint)
  assert.match(source, /请求键：<code>\{\{ form\.request_key \}\}<\/code>/)
  assert.match(source, /登记待确认草稿/)
  assert.match(source, /确认银行凭证/)
  assert.match(source, /放弃草稿/)
  assert.match(source, /预览不会占用额度/)
  assert.match(source, /remaining_candidate_amount === null \? '待核对'/)
  assert.match(source, /needsExplicitPrecision/)
  assert.match(source, /系统不会自动舍入历史金额/)
  assert.match(source, /登记结果尚未确认/)
  assert.match(source, /useUnsavedChangesGuard/)
  assert.match(source, /previewFingerprint/)
  assert.match(source, /预览已失效，请重新预览后再登记/)
  assert.match(source, /item\.verified === true/)
  assert.match(source, /逐条核实来源流水/)
  assert.match(source, /reviewConfirmed/)
  assert.match(source, /draftStorageKey/)
  assert.match(source, /clearLegacyDraftSnapshot/)
  assert.match(source, /draftRestoredRequiresEvidence/)
  assert.match(source, /storageKey\('sunjack:cash-event:request-identity:v1'\)/)
  assert.match(source, /sessionStorage\.setItem\(identityStorageKey, JSON\.stringify\(\{ event_no: form\.event_no, request_key: form\.request_key, saved_at: Date\.now\(\), attempted \}\)\)/)
  assert.doesNotMatch(source, /localStorage\.setItem/)
  assert.match(source, /markAllocationEdited/)
  assert.match(source, /allocationAmountBaseline/)
  assert.match(source, /confirmedSettlementEvents/)
  assert.match(source, /关联结汇事件/)
  assert.ok(source.includes('bank_net_amount: String(form.bank_net_amount'))
  assert.ok(source.includes("fee_amount: form.fee_mode === 'included' ? String(form.fee_amount"))
  assert.match(source, /sourceRequestId/)
  assert.doesNotMatch(source, /verified: true \}\)\}/)
})

test('cash event page keeps bank facts separate from legacy receipt and settlement data', async () => {
  const source = await readFile(pageUrl, 'utf8')
  assert.match(source, /结汇不新增客户收款，也不改变应收核销/)
  assert.match(source, /参考折算只用于对照，不代表银行实际到账/)
  assert.match(source, /selected\?\.status === 'pending'/)
  assert.doesNotMatch(source, /\/transactions\/.*\/allocate/)
})

test('independent fees offer an optional settlement and serialize no selection as null', async () => {
  const source = await readFile(pageUrl, 'utf8')
  assert.match(source, /关联结汇事件（可选）/)
  assert.match(source, /<select v-model="form.fee_for"><option value="">不关联结汇<\/option>/)
  assert.match(source, /fee_for: optionalSettlementId\(form.fee_for\)/)
  assert.doesNotMatch(source, /if \(form.kind === 'bank_fee' && !form.fee_for\)/)
  assert.match(source, /独立银行扣费使用单独的人民币手续费来源/)
})
