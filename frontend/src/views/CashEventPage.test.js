import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const pageUrl = new URL('./CashEventPage.vue', import.meta.url)
const formUrl = new URL('../components/CashEventEntryForm.vue', import.meta.url)

test('cash event page uses the shared entry form and keeps review actions', async () => {
  const page = await readFile(pageUrl, 'utf8')
  const form = await readFile(formUrl, 'utf8')
  for (const endpoint of [
    /api\.get\('\/rmb-cash-events\/'\)/,
    /\/confirm\//,
    /\/cancel\//,
  ]) assert.match(form, endpoint)
  assert.match(page, /<CashEventEntryForm/)
  assert.match(form, /api\.post\('\/rmb-cash-events\/preview\/'/)
  assert.match(form, /api\.post\('\/rmb-cash-events\/'/)
  assert.match(form, /duplicate-candidates/)
  assert.match(form, /确认银行凭证/)
  assert.match(form, /放弃草稿/)
  assert.match(form, /previewFingerprint/)
  assert.match(form, /remaining_candidate_amount === null/)
  assert.match(form, /needsExplicitPrecision/)
  assert.match(form, /item\.verified === true/)
  assert.match(form, /useUnsavedChangesGuard/)
  assert.match(form, /登记结果尚未确认/)
})

test('cash event form keeps system identifiers and file hashes out of visible copy', async () => {
  const source = await readFile(formUrl, 'utf8')
  const template = source.slice(source.indexOf('<template>'))
  assert.match(template, /新增资金事件/)
  assert.match(template, /预览结汇信息/)
  assert.match(template, /银行凭证文件/)
  assert.match(template, /核对说明/)
  assert.match(template, /实际到账日期/)
  assert.match(template, /银行净额（CNY）/)
  assert.match(template, /银行参考号/)
  assert.match(template, /暂无匹配的资金账户/)
  assert.match(template, /历史记录缺少实际凭证，请补传原始文件/)
  assert.doesNotMatch(template, /请求键|SHA256|后端预览|SYNTH|事件编号<input/)
  assert.match(source, /gross_rmb_amount: String\(form\.gross_rmb_amount/)
  assert.doesNotMatch(source, /actual_rate: actualRate\(\)/)
  assert.match(source, /function bankNetAmount\(\)/)
  assert.match(template, /扣费前兑换额（CNY）/)
  assert.match(template, /银行净到账（CNY）/)
  assert.match(template, /实际汇率/)
  assert.doesNotMatch(template, /@click\.self/)
})

test('cash events remain separate from receipt and installment accounting', async () => {
  const page = await readFile(pageUrl, 'utf8')
  const form = await readFile(formUrl, 'utf8')
  assert.match(page, /客户收款和应收核销仍按原流程保存/)
  assert.match(form, /source_receipt_id/)
  assert.match(form, /未分配预收仍显示为单独来源，不计作订单计划核销/)
  assert.match(form, /selected\?\.sources/)
  assert.match(page, /银行净额以实际凭证为准/)
  assert.doesNotMatch(form, /\/transactions\/.*\/allocate/)
})
