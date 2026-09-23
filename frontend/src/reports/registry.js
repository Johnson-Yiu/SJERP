// Stable IDs are public: pages can embed these blocks without the report center.
export const reportBlocks = {
  'sales-trend': { title: '销售趋势', source: 'sales', group_by: 'time', view: 'line' },
  'sales-region': { title: '区域销售', source: 'sales', group_by: 'region', view: 'bar' },
  'sales-country': { title: '国家销售', source: 'sales', group_by: 'country', view: 'bar' },
  'sales-customer': { title: '客户销售排行', source: 'sales', group_by: 'customer', view: 'bar' },
  'sales-product': { title: '产品销售排行', source: 'sales', group_by: 'product', view: 'bar' },
  'sales-sku': { title: 'SKU 销售排行', source: 'sales', group_by: 'sku', view: 'bar' },
  'sales-category': { title: '产品类别销售', source: 'sales', group_by: 'category', view: 'donut' },
  'sales-owner': { title: '负责人销售', source: 'sales', group_by: 'owner', view: 'bar' },
  'purchase-trend': { title: '采购趋势', source: 'purchase', group_by: 'time', view: 'line' },
  'purchase-supplier': { title: '供应商采购排行', source: 'purchase', group_by: 'supplier', view: 'bar' },
  'purchase-sku': { title: 'SKU 采购排行', source: 'purchase', group_by: 'sku', view: 'bar' },
  'customers-growth': { title: '客户增长趋势', source: 'customers', group_by: 'time', metric: 'count', view: 'line' },
  'customers-source': { title: '客户来源分布', source: 'customers', group_by: 'source', metric: 'count', view: 'donut' },
  'cash-trend': { title: '净现金流趋势', source: 'cash', group_by: 'time', view: 'line' },
  'cash-category': { title: '收支分类', source: 'cash', group_by: 'category', view: 'bar' },
  'inventory-warehouse': { title: '仓库库存变动', source: 'inventory', group_by: 'warehouse', metric: 'quantity', view: 'bar' },
}

export function resolveBlock(id, overrides = {}) {
  return { source: 'sales', group_by: 'time', grain: 'month', metric: 'amount', view: 'bar', ...reportBlocks[id], ...overrides }
}

export function localDate(value) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
}

export function datePreset(preset, now = new Date()) {
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  let start = new Date(end)
  if (preset === 'week') start.setDate(start.getDate() - (start.getDay() + 6) % 7)
  if (preset === 'month') start.setDate(1)
  if (preset === 'quarter') start = new Date(end.getFullYear(), Math.floor(end.getMonth() / 3) * 3, 1)
  if (preset === 'year') start = new Date(end.getFullYear(), 0, 1)
  if (preset === 'last-month') { start = new Date(end.getFullYear(), end.getMonth() - 1, 1); end.setDate(0) }
  if (preset === 'last-year') { start = new Date(end.getFullYear() - 1, 0, 1); end.setFullYear(end.getFullYear() - 1, 11, 31) }
  if (preset === '30' || preset === '90') start.setDate(start.getDate() - Number(preset) + 1)
  return { date_from: localDate(start), date_to: localDate(end) }
}
