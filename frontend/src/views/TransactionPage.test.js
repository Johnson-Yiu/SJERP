import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const pageUrl = new URL('./TransactionPage.vue', import.meta.url)
const settlementUrl = new URL('../components/CashEventEntryForm.vue', import.meta.url)

test('transaction form distinguishes refunds from order expenses', async () => {
  const source = await readFile(pageUrl, 'utf8')

  assert.match(source, /客户退款（原收款退回）/)
  assert.match(source, /供应商退款（原付款退回）/)
  assert.match(source, /value: 'order_expense', label: '订单费用'/)
  assert.match(source, /const orderExpenseCategories = \['样品与打样', '模具', '验货', '运费', '报关', '仓储', '佣金'/)
  assert.match(source, /用于退回已经收到的订单货款；售后赔偿、运费补贴等请登记为订单费用。/)
  assert.match(source, /用于供应商退回已经支付的采购款。/)
  assert.doesNotMatch(source, /客户退款\/折让/)
  assert.doesNotMatch(source, /供应商退款\/返利/)
})

test('period expense changes only its dropdown label and preserves the category value', async () => {
  const source = await readFile(pageUrl, 'utf8')
  assert.match(source, /value: 'period_expense', label: '其他期间费用', displayLabel: '其他期间费用（如水电费、物业费、软件订阅费等）'/)
  assert.match(source, /option\.displayLabel \|\| option\.label/)
  assert.match(source, /form\.category = meta\.label/)
  assert.doesNotMatch(source, /form\.category\s*=\s*option\.displayLabel/)
})

test('customer receipts expand the shared settlement flow and retain direct CNY guidance', async () => {
  const source = await readFile(pageUrl, 'utf8')
  const settlement = await readFile(settlementUrl, 'utf8')
  assert.match(source, /登记收汇记录/)
  assert.match(source, /本笔收款无需登记外币结汇/)
  assert.match(source, /保存收款并继续/)
  assert.match(source, /type="button" class="settlement-expand" @click="settlementOpen = true">登记收汇记录/)
  assert.match(source, /mode="linked"/)
  assert.match(source, /:receipt="savedReceipt"/)
  assert.match(settlement, /source_receipt_id/)
  assert.match(source, /重试只会提交结汇信息/)
  assert.match(source, /if \(savedReceipt\.value\) return/)
  assert.match(source, /v-if="!savedReceipt"/)
  assert.match(source, /api\.post\('\/transactions\/'/)
  assert.match(source, /saveOrVerifyCustomerReceipt/)
})

test('non-receipt transaction saves retain their existing recovery path', async () => {
  const source = await readFile(pageUrl, 'utf8')
  assert.match(source, /if \(form\.kind !== 'customer_receipt'\) \{[\s\S]*?api\.post\('\/transactions\/', payload\)/)
  assert.match(source, /编号重复不代表本次保存成功/)
  assert.match(source, /saveOutcome === 'unknown' \? '按原编号重试'/)
})

test('transaction entry exposes bank-fee responsibility and original receipt settlement detail', async () => {
  const source = await readFile(pageUrl, 'utf8')

  assert.match(source, /客户汇款金额（\{\{ form\.currency \}\}）/)
  assert.match(source, /银行扣费 \{\{ form\.currency \}\}/)
  assert.match(source, /我方承担（凭证齐全后按客户汇款额核销）/)
  assert.match(source, /客户承担（保留未收差额）/)
  assert.match(source, /待查（保留未收差额）/)
  assert.match(source, /remitted_amount_display/)
  assert.doesNotMatch(source, /remittance_amount_display/)
  assert.match(source, /登记结汇到账/)
  assert.match(source, /扣费前兑换额/)
  assert.match(source, /与参考汇率差额/)
  assert.match(source, /cash_settlements/)
  assert.match(source, /voucher-download/)
})

test('transaction detail records authorized rounding without creating a cash receipt', async () => {
  const source = await readFile(pageUrl, 'utf8')

  assert.match(source, /const writeoffPlanSource = computed\(\(\) => writeoffTarget\.value \|\| detailTarget\.value\)/)
  assert.match(source, /登记授权抹零/)
  assert.match(source, /writeoff\/`/)
  assert.match(source, /request_key: writeoffRequestKey\.value/)
  assert.match(source, /减少未结应收，不新增现金收款。/)
  assert.match(source, /confirmed_actor/)
  assert.match(source, /客户确认抹零的原因/)
  assert.match(source, /订单降价或质量赔偿请使用正式订单修订及对应依据。/)
})

test('transaction summary includes rows attributed through receipt allocations', async () => {
  const source = await readFile(pageUrl, 'utf8')

  assert.match(source, /label: '业务归属流水', value: rows\.value\.filter\(row => row\.order \|\| row\.purchase_order \|\| row\.order_no \|\| row\.purchase_no \|\| \(row\.allocations \|\| \[\]\)\.length\)/)
  assert.match(source, /含核销分配及直接关联合同/)
})

test('allocated advances display as receipts or supplier payments while retaining their unallocated balance', async () => {
  const source = await readFile(pageUrl, 'utf8')

  assert.match(source, /function transactionKindLabel\(row\)[\s\S]*?row\?\.kind === 'unallocated_advance' && Number\(row\.allocated_amount\) > 0\) return '客户收款'/)
  assert.match(source, /row\?\.kind === 'unallocated_payment' && Number\(row\.allocated_amount\) > 0\) return '供应商付款'/)
  assert.match(source, /未分配 \{\{ row\.currency \}\} \{\{ formatMoney\(unallocatedAmount\(row\)\) \}\}/)
})
