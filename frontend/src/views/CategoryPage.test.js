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
