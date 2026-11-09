const errorFieldLabels = {
  quantity: '数量', unit_price: '单价', currency: '币种', exchange_rate: '汇率',
  customer: '客户', buyer_company_name: '买方公司', supplier: '供应商', items: '商品明细',
  sku: 'SKU', warehouse: '仓库', movement_date: '流水日期', unit_cost: '单位成本',
  related_orders: '关联订单', trade_unit: '交易单位', reference: '业务参考号',
}

function errorPathLabel(path) {
  return path.map((part, index) => {
    if (part === 'items' && typeof path[index + 1] === 'object') return ''
    return typeof part === 'string' ? (errorFieldLabels[part] || '') : `第 ${part.item + 1} 条商品`
  }).filter(Boolean).join(' · ')
}

export function formatApiError(data) {
  const messages = []
  const visit = (value, path = []) => {
    if (value == null || value === '') return
    if (Array.isArray(value)) {
      value.forEach((entry, index) => visit(entry, path.at(-1) === 'items' ? [...path, { item: index }] : path))
      return
    }
    if (typeof value === 'object') {
      for (const [key, entry] of Object.entries(value)) {
        if (entry == null || entry === '') continue
        if (key === 'detail' || key === 'non_field_errors') visit(entry, path)
        else visit(entry, [...path, key])
      }
      return
    }
    const message = String(value).trim()
    if (!message) return
    const label = errorPathLabel(path)
    messages.push(label ? `${label}：${message}` : message)
  }
  visit(data)
  return [...new Set(messages)].join('；')
}

export function apiErrorMessage(errorOrData) {
  if (errorOrData instanceof Error || (errorOrData && typeof errorOrData === 'object' && ('status' in errorOrData || errorOrData.isAxiosError || errorOrData.isApiError))) {
    const status = Number(errorOrData.status || errorOrData.response?.status || 0)
    if (!status) {
      if (errorOrData.code === 'ECONNABORTED' || errorOrData.code === 'ETIMEDOUT') return '连接服务器超时，请检查网络后重试。'
      if (errorOrData.isApiError || errorOrData.isAxiosError) return '网络连接失败，请检查网络后重试。'
      return errorOrData.message || '请求失败，请稍后重试。'
    }
    if (status >= 500) return '服务器暂时不可用，请稍后重试。'
    const formatted = formatApiError(errorOrData.data ?? errorOrData.response?.data)
    if (formatted) return formatted
    return status === 400 ? '请求未能通过校验，请检查填写内容。' : `请求失败（HTTP ${status}），请稍后重试。`
  }
  return formatApiError(errorOrData) || '请求失败，请稍后重试。'
}
