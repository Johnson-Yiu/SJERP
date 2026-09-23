import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

test('related create modal supports inherited relationships', async () => {
  const source = await readFile(new URL('./RelatedCreateModal.vue', import.meta.url), 'utf8')
  assert.match(source, /isInherited\(field\[0\]\)/)
  assert.match(source, /props\.query\.sku/)
  assert.match(source, /:disabled="isInherited\('customer'\)"/)
  assert.doesNotMatch(source, /已继承/)
})

test('detail relation context carries parent customer and contact', async () => {
  const source = await readFile(new URL('./EntityDetailModal.vue', import.meta.url), 'utf8')
  assert.match(source, /if \(root === 'contacts'\) \{ ids\.contact = id; ids\.customer = sectionRowId\('company'\) \}/)
  assert.match(source, /if \(root === 'transactions'\) \{ ids\.customer = sectionRowId\('customer'\); ids\.supplier = sectionRowId\('supplier'\); ids\.order = sectionRowId\('order'\); ids\.purchase_order = sectionRowId\('purchase-order'\) \}/)
  assert.match(source, /if \(entity === 'follow-ups'\) return Object\.fromEntries\(\[\['customer', ids\.customer\], \['contact', ids\.contact\]\]/)
  assert.match(source, /entity === 'purchase-orders'/)
})

test('follow-up rows open the shared detailed follow-up view', async () => {
  const source = await readFile(new URL('./EntityDetailModal.vue', import.meta.url), 'utf8')

  assert.match(source, /const targetEntity = row\._target_entity \|\| activeSection\.value\?\.entity/)
  assert.match(source, /currentEntity === 'follow-ups'/)
  assert.match(source, /跟进详情/)
})

test('follow-up creation links days-after input to the next follow-up date', async () => {
  const source = await readFile(new URL('./RelatedCreateModal.vue', import.meta.url), 'utf8')

  assert.match(source, /followUpDays/)
  assert.match(source, /updateFollowUpDate/)
  assert.match(source, /下次跟进天数/)
  assert.match(source, /setFollowUpDate/)
})

test('related create payload serializes empty optional dates as null', async () => {
  const source = await readFile(new URL('./RelatedCreateModal.vue', import.meta.url), 'utf8')

  assert.match(source, /if \(type === 'date' && value === ''\) value = null/)
  assert.match(source, /form\.next_follow_up = ''/)
})
