import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./CategoryPage.vue', import.meta.url)

test('creating a category attribute updates the local category state without reloading the page', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /function applyCreatedAttribute\(attribute\)/)
  assert.match(source, /categories\.value\.forEach\(rebuildEffectiveAttributes\)/)
  assert.match(source, /const response = await api\.post\('\/category-attributes\//)
  assert.match(source, /applyCreatedAttribute\(response\.data\)/)
  assert.doesNotMatch(source, /addingAttribute\.value = false; await load\(selectedId\.value\)/)
})

test('category template explains that published SKU plans do not auto-mutate', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /分类参数是产品的默认参数模板。已有已发布 SKU 参数方案的产品不会自动跟随模板变化；如需应用变化，请在产品 SKU 参数方案中分析并发布。/)
})
