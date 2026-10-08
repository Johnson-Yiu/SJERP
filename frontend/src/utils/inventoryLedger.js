export const movementTypes = { adjust_in:'盘盈入库', adjust_out:'盘亏出库', sample_out:'样品出库', return_in:'客户退回', transfer_in:'调拨入库', transfer_out:'调拨出库', production_in:'生产入库', production_out:'生产领料', other_in:'其他入库', other_out:'其他出库' }
const inbound = new Set(['purchase_in','adjust_in','return_in','transfer_in','production_in','other_in'])
const outbound = new Set(['sale_out','adjust_out','sample_out','transfer_out','production_out','other_out'])
export function movementDirection(row) { return inbound.has(row.type) ? 'in' : outbound.has(row.type) ? 'out' : '' }
export function movementSource(row) { return row.source_type === 'reversal' ? 'reversal' : row.is_automatic === true ? 'automatic' : row.source_type === 'manual' ? 'manual' : '' }
export const sourceLabels = { automatic:'系统自动', manual:'手工登记', reversal:'冲销生成' }
export function movementStatus(row) { return row.source_type === 'reversal' ? '冲销流水' : row.is_reversed ? '已冲销' : '正常' }
export function ledgerFilters(query) { return { type: Object.hasOwn(movementTypes,query.type) ? query.type : '', direction: ['in','out'].includes(query.direction) ? query.direction : '', source: ['automatic','manual','reversal'].includes(query.source) ? query.source : '' } }
export function filteredMovements(rows,query) { const filters = ledgerFilters(query); return rows.filter(row => (!filters.type || row.type === filters.type) && (!filters.direction || movementDirection(row) === filters.direction) && (!filters.source || movementSource(row) === filters.source)) }
export function movementSummary(rows) { return [['流水记录',rows.length,'当前筛选结果'],['入库记录',rows.filter(row=>movementDirection(row)==='in').length,'库存增加'],['出库记录',rows.filter(row=>movementDirection(row)==='out').length,'库存减少'],['冲销记录',rows.filter(row=>movementSource(row)==='reversal').length,'冲销生成']].map(([label,value,hint])=>({label,value,hint})) }
export function movementUnit(row,skus=[]) { return row.trade_snapshot?.base_unit || skus.find(sku=>String(sku.id)===String(row.sku))?.unit || '' }
export function signedMovement(row,unit='') { const value=Number(row.signed_quantity); return Number.isFinite(value) ? `${value>0?'+':''}${value.toLocaleString('zh-CN')}${unit ? ` ${unit}` : ''}` : '—' }
