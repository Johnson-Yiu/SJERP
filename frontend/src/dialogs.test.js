import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

test('business pages use the shared dialog infrastructure instead of browser dialogs', async () => {
  const files = [
    'views/CategoryPage.vue', 'components/EntityDetailModal.vue', 'views/DocumentPage.vue', 'components/OrderDetailModal.vue',
    'views/PackagingPage.vue', 'components/ProductSkuManagement.vue', 'views/ProductPage.vue', 'views/PurchaseOrderPage.vue',
    'components/PurchaseCostAllocationModal.vue', 'components/QuoteDetailModal.vue', 'views/ResourcePage.vue', 'views/SKUPage.vue', 'components/RichTextEditor.vue',
  ]
  for (const file of files) {
    const source = await readFile(new URL(`./${file}`, import.meta.url), 'utf8')
    assert.match(source, /from ['"]\.\.\/dialogs['"]/, file)
    assert.doesNotMatch(source, /window\s*\.\s*(confirm|alert|prompt)/, file)
  }
})

test('the shared host exposes DOM-accessible controls for automation', async () => {
  const source = await readFile(new URL('./components/AppDialogHost.vue', import.meta.url), 'utf8')
  assert.match(source, /data-testid="dialog-confirm"/)
  assert.match(source, /data-testid="dialog-cancel"/)
  assert.match(source, /role="dialog"/)
  assert.match(source, /event\.key === 'Escape'/)
})
