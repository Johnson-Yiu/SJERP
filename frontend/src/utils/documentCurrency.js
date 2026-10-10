export function defaultExchangeRate(currency) {
  return currency === 'CNY' ? '1' : currency === 'USD' ? '7.2' : ''
}

export function skuDefaultPrice(sku, currency) {
  return sku?.currency === currency ? (sku.default_price ?? '') : ''
}

export function currencyHint(sku, currency, price) {
  if (!sku || sku.currency === currency || (price != null && price !== '')) return ''
  const defaultPrice = Number(sku.default_price || 0).toFixed(2)
  return `该 SKU 默认售价为 ${sku.currency || '未设置币种'} ${defaultPrice}，当前单据币种为 ${currency}，请填写本次售价。`
}

export function salesRateError(document) {
  if (!Number.isFinite(Number(document.exchange_rate)) || Number(document.exchange_rate) <= 0) return '请输入大于 0 的对人民币汇率。'
  if (document.currency === 'CNY' && Number(document.exchange_rate) !== 1) return '人民币单据的对人民币汇率必须为 1。'
  return ''
}

export async function changeDocumentCurrency(document, currency, skus, confirm) {
  if (currency === document.currency) return false
  const priced = (document.items || []).some(item => item.unit_price !== '' && item.unit_price != null)
  if (priced && !await confirm({ title: '切换单据币种', message: `切换币种将清除当前商品单价，并重新检查 SKU 默认售价。手工填写的 ${document.currency} 价格不会自动转换为 ${currency}。是否继续？`, confirmText: '继续切换' })) return false
  document.currency = currency
  document.exchange_rate = defaultExchangeRate(currency)
  for (const item of document.items || []) {
    const sku = skus.find(s => Number(s.id) === Number(item.sku))
    const price = skuDefaultPrice(sku, currency)
    item.unit_price = price === '' ? '' : Number((Number(price) * Number(item.trade_unit ? item.trade_snapshot?.factor || 1 : 1)).toFixed(4))
  }
  return true
}
