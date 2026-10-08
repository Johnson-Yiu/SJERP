// Presentation only: keep lifecycle values and the full explanation unchanged.
const labels = { lead: '线索', contact: '已联系', opportunity: '商机', customer: '正式客户', company: '返单客户' }
export function customerListStatus(value, fallback = value) {
  return labels[value] || fallback
}
