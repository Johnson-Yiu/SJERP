import { execFileSync } from 'node:child_process'
import { expect, test } from '@playwright/test'

const file = 'product-sku-price-currencies.spec.js'
test('SKU candidate table keeps cost and selling currencies separate', async ({ page }, info) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== file, 'Requires dedicated isolated data')
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, ['-c', `
import django
import json
django.setup()
from django.conf import settings
from test_support.isolated_runtime import verify_isolated_runtime
verify_isolated_runtime(settings=settings, database_must_exist=True)
from crm.models import Product, SKU
p = Product.objects.create(code='SKU-CURRENCY-03', name='Synthetic currency review')
for code, cost, currency in [('MIX', 12, 'CNY'), ('SAME', 12, 'USD'), ('UNKNOWN', 12, None), ('ZERO', 0, 'EUR')]:
    SKU(product=p, sku=code, unit='pcs', currency='USD', cost_currency=currency, cost_price=cost, default_price=20).save(preserve_unknown_cost_currency=True)
print(json.dumps(p.pk))
`], { cwd: new URL('../../backend/', import.meta.url), encoding: 'utf8' }))
  await page.setViewportSize({ width: 1366, height: 768 })
  await page.goto(`/products?detail=${fixture}&tab=skus`, { waitUntil: 'domcontentloaded' })
  const table = page.locator('.candidate-table')
  for (const [code, cost] of [['MIX', '12\\.0+ CNY'], ['SAME', '12\\.0+ USD'], ['UNKNOWN', '12\\.0+ 币种待核实'], ['ZERO', '0\\.0+ EUR']]) {
    const cell = table.getByRole('row').filter({ has: page.getByRole('button', { name: code, exact: true }) }).getByRole('cell').nth(5)
    await expect(cell).toHaveText(new RegExp(`^成本 ${cost}\\s*售价 20\\.0+ USD$`))
  }
  await table.screenshot({ path: info.outputPath('sku-cost-sale-currencies.png') })
})
