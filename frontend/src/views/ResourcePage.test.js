import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { runInNewContext } from 'node:vm'
import { resourceConfigs } from '../resourceConfigs.js'

test('resource payload serializes empty optional dates as null', async () => {
  const source = await readFile(new URL('./ResourcePage.vue', import.meta.url), 'utf8')

  assert.match(source, /if \(type === 'date' && value === ''\) value = null/)
})

test('customer projections are visible but not editable customer fields', async () => {
  const customer = resourceConfigs.customers
  const page = await readFile(new URL('./ResourcePage.vue', import.meta.url), 'utf8')
  const detail = await readFile(new URL('../components/EntityDetailModal.vue', import.meta.url), 'utf8')

  assert.equal(customer.columns.some(column => column[0] === 'next_follow_up'), true)
  assert.equal(customer.fields.some(field => field[0] === 'next_follow_up'), false)
  assert.equal(customer.columns.some(column => column[0] === 'status'), true)
  assert.equal(customer.fields.some(field => field[0] === 'status'), false)
  assert.match(customer.description, /客户阶段会根据报价和订单自动更新/)
  assert.match(page, /contact: '已建立联系'/)
  assert.match(page, /opportunity: '已进入报价阶段'/)
  assert.match(page, /customer: '已有1张正式订单'/)
  assert.match(page, /company: '已有2张及以上正式订单'/)
  assert.match(detail, /currentEntity === 'customers' && item\[0\] === '下次跟进'/)
  assert.match(detail, /随最新跟进自动更新/)
})

test('customer detail shortcuts require the target module action permission', async () => {
  const detail = await readFile(new URL('../components/EntityDetailModal.vue', import.meta.url), 'utf8')

  assert.match(detail, /currentEntity === 'customers' && can\('followups', 'create'\)/)
  assert.match(detail, /currentEntity === 'customers' && hasRelationCustomerId && can\('quotes', 'create'\)/)
  assert.match(detail, /currentEntity !== 'inventory-movements' && can\(currentEntity, 'update'\)/)
  assert.match(detail, /can\('followups', 'update'\).*编辑/)
  assert.match(detail, /can\('followups', 'delete'\).*删除/)
})

test('customer, product and SKU details expose a permission-gated report-center shortcut with a safe return path', async () => {
  const detail = await readFile(new URL('../components/EntityDetailModal.vue', import.meta.url), 'utf8')

  assert.match(detail, /analysisDimensions = \{ customers: 'customer', products: 'product', skus: 'sku' \}/)
  assert.match(detail, /canViewBusinessAnalysis = computed\(\(\) => Boolean\(isRoot.value && analysisDimension.value && can\('reports', 'view'\)/)
  assert.match(detail, /path: '\/reports'/)
  assert.match(detail, /\[`filter_\$\{analysisDimension.value\}`\]: String\(currentId.value\)/)
  assert.match(detail, /returnTo: detailReturnPath\(\)/)
  assert.match(detail, /查看经营分析/)
})

test('automatic inventory movements are read-only while manual movements are reversed, not deleted', async () => {
  const source = await readFile(new URL('./ResourcePage.vue', import.meta.url), 'utf8')
  const detail = await readFile(new URL('../components/EntityDetailModal.vue', import.meta.url), 'utf8')
  const movementConfig = resourceConfigs['inventory-movements']
  const typeOptions = movementConfig.fields.find(field => field[0] === 'type')[4]
  const helper = source.match(/function isReadOnlyAutomaticMovement\(row\) \{[^}]+\}/)?.[0]
  const context = { props: { config: { endpoint: 'inventory-movements' } } }

  assert.ok(helper)
  runInNewContext(`${helper}; this.isReadOnlyAutomaticMovement = isReadOnlyAutomaticMovement`, context)
  assert.equal(context.isReadOnlyAutomaticMovement({ is_automatic: true }), true)
  assert.equal(context.isReadOnlyAutomaticMovement({ is_automatic: false }), false)
  assert.match(source, /title="查看详情"/)
  assert.match(source, /function canReverseInventoryMovement\(row\)/)
  assert.match(source, /reverseInventoryMovement\(row\)/)
  assert.match(source, /inputDialog\(\{/)
  assert.match(source, /\/inventory-movements\/\$\{row\.id\}\/reverse\//)
  assert.match(source, /title="冲销"/)
  assert.match(source, /config\.endpoint !== 'inventory-movements' && !isReadOnlyAutomaticMovement\(row\)/)
  assert.match(detail, /isRoot && currentEntity !== 'inventory-movements'/)
  assert.deepEqual(Object.keys(typeOptions), [
    'adjust_in', 'adjust_out', 'sample_out', 'return_in', 'transfer_in', 'transfer_out',
    'production_in', 'production_out', 'other_in', 'other_out',
  ])
  assert.doesNotMatch(JSON.stringify(typeOptions), /purchase_in|sale_out/)
})

test('follow-up history summary is distinguished from the current dashboard obligation', async () => {
  const source = await readFile(new URL('./ResourcePage.vue', import.meta.url), 'utf8')
  assert.match(source, /计划日期已到记录/)
  assert.match(source, /历史跟进记录统计；当前待跟进以经营概览为准/)
})

test('customer ownership uses scoped employee options and sends an explicit clear as null', async () => {
  const customer = resourceConfigs.customers
  const page = await readFile(new URL('./ResourcePage.vue', import.meta.url), 'utf8')
  const organization = await readFile(new URL('./OrganizationPage.vue', import.meta.url), 'utf8')
  const ownerField = customer.fields.find(field => field[0] === 'owner_profile')

  assert.ok(ownerField)
  assert.equal(ownerField[2], 'remote')
  assert.equal(ownerField[4], 'customers/owner-options')
  assert.equal(ownerField[5], 'label')
  assert.equal(customer.fields.some(field => field[0] === 'owner'), false)
  assert.ok(page.includes('accessState.operator?.employee_profile_id'))
  assert.match(page, /data_scope === 'self'/)
  assert.match(page, /ownerProfileReadOnly/)
  assert.match(page, /if \(type === 'remote'\) value = value \? Number\(value\) : null/)
  assert.match(page, /data\[name\] = value/)
  assert.doesNotMatch(page, /delete data\.owner_profile/)
  assert.match(organization, /数据范围当前首先用于客户\/CRM\/销售记录/)
})

