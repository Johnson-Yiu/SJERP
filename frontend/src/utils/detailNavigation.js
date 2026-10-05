export function orderDetailLocation(orderId) {
  return { path: '/orders', query: { detail: String(orderId) } }
}

export function purchaseDetailLocation(purchaseId) {
  return { path: '/purchase-orders', query: { detail: String(purchaseId) } }
}
