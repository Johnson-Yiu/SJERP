<script setup>
import { computed } from 'vue'
import { scaleDecimalInput } from '../utils/decimalInput'
import { baseQuantity } from '../utils/tradeUnits'
const props = defineProps({ line: { type: Object, required: true }, sku: Object, supplier: [String, Number], priceField: { type: String, default: 'unit_price' }, preserveBaseQuantity: Boolean, exactDecimalPrice: Boolean, historicalUnit: [String, Number] })
const options = computed(() => (props.sku?.trade_units || []).filter(u => (u.active || u.id === Number(props.line.trade_unit) || u.id === Number(props.historicalUnit || props.line._historical_trade_unit)) && (!props.supplier || !u.supplier || Number(u.supplier) === Number(props.supplier))))
function select(event) {
  const previousFactor = props.line.trade_unit ? props.line.trade_snapshot?.factor || 1 : 1
  const previous = Number(previousFactor)
  const previousQuantity = baseQuantity(props.line)
  const unit = options.value.find(u => u.id === Number(event.target.value))
  props.line.trade_unit = unit?.id || null
  props.line.trade_snapshot = unit ? { name: unit.name, unit: unit.unit, factor: unit.factor, base_unit: unit.base_unit, allow_fraction: unit.allow_fraction } : { unit: props.sku?.unit, base_unit: props.sku?.unit, factor: '1' }
  if (props.preserveBaseQuantity) props.line.quantity = Number((previousQuantity / Number(unit?.factor || 1)).toPrecision(12))
  if (props.priceField && props.line[props.priceField] !== '' && props.line[props.priceField] != null) {
    props.line[props.priceField] = props.exactDecimalPrice
      ? scaleDecimalInput(props.line[props.priceField], previousFactor, unit?.factor || 1)
      : Number((Number(props.line[props.priceField]) / previous * Number(unit?.factor || 1)).toFixed(4))
  }
}
</script>
<template>
  <div class="trade-unit-picker">
    <select :value="line.trade_unit || ''" aria-label="交易单位与包装规格" @change="select">
      <option value="">{{ sku?.unit || line.trade_snapshot?.base_unit || '基础单位' }}（基础单位）</option>
      <option v-for="unit in options" :key="unit.id" :value="unit.id">{{ unit.name }} · {{ unit.factor }} {{ unit.base_unit }}/{{ unit.unit }}{{ unit.active ? '' : '（历史）' }}</option>
      <option v-if="line.trade_unit && !options.some(u => u.id === Number(line.trade_unit))" :value="line.trade_unit">{{ line.trade_snapshot?.name }}（历史规格）</option>
    </select>
    <small v-if="line.trade_unit">{{ line.quantity || 0 }} {{ line.trade_snapshot?.unit }} = {{ Number(baseQuantity(line).toFixed(2)) }} {{ line.trade_snapshot?.base_unit }}</small>
    <small v-if="line.trade_unit && !line.trade_snapshot?.allow_fraction && Number(line.quantity) % 1">此规格仅支持整包装；拆零请使用基础单位。</small>
  </div>
</template>
<style scoped>
.trade-unit-picker{display:grid;gap:4px;min-width:120px;margin-top:6px}.trade-unit-picker select{max-width:100%;width:100%;padding:7px;border:1px solid #d0dfd8;border-radius:6px;background:#fff;color:#244b40;font:inherit}.trade-unit-picker small{color:#5a766b;font-size:12px;white-space:normal}
</style>
