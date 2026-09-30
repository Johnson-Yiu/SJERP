import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = path => readFile(new URL(path, import.meta.url), 'utf8')

test('core management lists and selectors use the tested all-pages loader', async () => {
  const [resource, documents, products, packaging, sku, quoteEditor] = await Promise.all([
    source('./ResourcePage.vue'),
    source('./DocumentPage.vue'),
    source('./ProductPage.vue'),
    source('./PackagingPage.vue'),
    source('./SKUPage.vue'),
    source('../components/QuoteEditorModal.vue'),
  ])

  assert.match(resource, /import \{ api, listAll \} from '\.\.\/api'/)
  assert.match(resource, /rows\.value = await listAll\(/)
  assert.match(resource, /options\[field\[4\]\] = await listAll\(/)

  assert.match(documents, /rows\.value = await listAll\(`\/\$\{props\.type\}\//)
  assert.match(documents, /listAll\('\/customers\/'\)/)
  assert.match(documents, /listAll\('\/skus\/'\)/)
  assert.match(documents, /listAll\('\/quotes\/'\)/)

  assert.match(products, /listAll\('\/products\//)
  assert.match(products, /listAll\('\/suppliers\/'\)/)
  assert.match(products, /api\.get\('\/categories\/tree\/'\)/)
  assert.match(packaging, /listAll\('\/packaging-templates\/'\)/)
  assert.match(packaging, /listAll\('\/suppliers\/'\)/)
  assert.match(packaging, /listAll\('\/skus\/'\)/)

  assert.match(sku, /listAll\('\/packaging-templates\/'\)/)
  assert.match(sku, /listAll\('\/suppliers\/'\)/)
  assert.match(sku, /listAll\('\/supplier-skus\/', \{ params: \{ sku: skuId \} \}\)/)
  assert.match(quoteEditor, /listAll\('\/contacts\/', \{ params: \{ customer: customer\.id \} \}\)/)
  assert.match(quoteEditor, /listAll\('\/packaging-templates\/'\)/)
})
