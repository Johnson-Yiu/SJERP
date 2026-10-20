<script setup>
import { computed, ref } from 'vue'
import CategoryPathFilter from './CategoryPathFilter.vue'
import { categoryContains } from '../utils/categoryPaths'

const props = defineProps({
  skus: { type: Array, default: () => [] },
  modelValue: { type: Array, default: () => [] },
  activeId: { type: [String, Number], default: '' },
  title: { type: String, default: '选择 SKU' },
  searchPlaceholder: { type: String, default: '搜索 SKU、型号或描述' },
  height: { type: [String, Number], default: 268 },
  showPrice: { type: Boolean, default: true },
})
const emit = defineEmits(['update:modelValue', 'update:activeId'])
const search = ref('')
const category = ref('')

function categoryNames(sku) {
  const values = Array.isArray(sku?.category_names) ? sku.category_names : [sku?.category_name || sku?.product_category_name]
  return values.map(value => String(value || '').trim()).filter(Boolean)
}
const categories = computed(() => [...new Set(props.skus.flatMap(categoryNames))].sort((a, b) => a.localeCompare(b, 'zh-CN')))
const selectedIds = computed(() => new Set((props.modelValue || []).map(value => String(value))))
const activeSku = computed(() => props.skus.find(sku => String(sku.id) === String(props.activeId)) || props.skus.find(sku => selectedIds.value.has(String(sku.id))) || null)
const filteredSkus = computed(() => {
  const terms = search.value.trim().toLowerCase().split(/\s+/).filter(Boolean)
  return props.skus.filter(sku => {
    if (category.value && !categoryNames(sku).some(path => categoryContains(category.value, path))) return false
    if (!terms.length) return true
    const text = `${sku.sku || ''} ${sku.sku_code || ''} ${sku.sales_model || ''} ${sku.product_name || ''} ${sku.display_name_cn || ''} ${sku.specification || ''} ${sku.description_cn || ''} ${sku.description_en || ''}`.toLowerCase()
    return terms.every(term => text.includes(term))
  })
})
function label(sku) { return sku.display_name_cn || sku.product_name || sku.sku || '未命名 SKU' }
function skuCode(sku) { return sku.sku_code || sku.sku || '—' }
function toggle(sku) {
  const next = [...selectedIds.value]
  const id = String(sku.id)
  const index = next.indexOf(id)
  if (index >= 0) next.splice(index, 1)
  else next.push(id)
  emit('update:modelValue', next)
  emit('update:activeId', next.includes(id) ? id : (next.at(-1) || ''))
}
function activate(sku) { emit('update:activeId', String(sku.id)) }
</script>

<template>
  <div class="sku-selection-panel" :style="{ '--sku-picker-height': `${height}px` }">
    <section class="sku-picker-list">
      <div class="sku-picker-head">
        <strong>{{ title }}</strong>
        <div class="sku-picker-filters">
          <input v-model.trim="search" type="search" :placeholder="searchPlaceholder" :aria-label="searchPlaceholder" />
          <CategoryPathFilter v-model="category" :paths="categories" />
        </div>
      </div>
      <div class="sku-picker-options">
        <label v-for="sku in filteredSkus" :key="sku.id" :class="{ active: String(activeSku?.id) === String(sku.id) }" @click="activate(sku)">
          <input type="checkbox" :checked="selectedIds.has(String(sku.id))" @click.stop="toggle(sku)" />
          <span><b>{{ label(sku) }}</b><small class="sku-identifiers"><span>SKU: {{ skuCode(sku) }}</span><span>Sales Model: {{ sku.sales_model || '—' }}</span></small></span>
          <em v-if="showPrice">{{ sku.currency || '币种未设置' }} {{ Number(sku.default_price || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</em>
        </label>
        <p v-if="!filteredSkus.length">没有匹配的 SKU。</p>
      </div>
    </section>
    <aside class="sku-picker-preview">
      <template v-if="activeSku">
        <small>已选 SKU 详情</small>
        <strong>{{ label(activeSku) }}</strong>
        <dl><div><dt>SKU Code</dt><dd>{{ skuCode(activeSku) }}</dd></div><div><dt>Sales Model</dt><dd>{{ activeSku.sales_model || '—' }}</dd></div><div><dt>单位 / 默认单价</dt><dd>{{ activeSku.unit || 'pcs' }} / {{ activeSku.currency || '币种未设置' }} {{ Number(activeSku.default_price || 0).toFixed(2) }}</dd></div></dl>
        <slot name="preview" :sku="activeSku" />
      </template>
      <p v-else>从左侧勾选 SKU 后，可在这里查看详情。</p>
    </aside>
  </div>
</template>

<style scoped>
.sku-selection-panel{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(270px,.85fr);height:var(--sku-picker-height);margin:0 0 14px;border:1px solid #dbe5df;border-radius:10px;overflow:hidden;background:#fff}.sku-picker-list{display:flex;flex-direction:column;min-width:0;min-height:0;overflow:hidden;border-right:1px solid #e4ece7}.sku-picker-head{padding:11px;border-bottom:1px solid #e8efeb}.sku-picker-head strong{display:block;margin-bottom:8px;font-size:var(--text-body)}.sku-picker-filters{display:grid;grid-template-columns:minmax(0,1fr) 130px;gap:7px}.sku-picker-head input,.sku-picker-head select{width:100%;border:1px solid #d7e1dc;border-radius:7px;padding:8px 10px;background:#fff;font-size:var(--text-body)}.sku-picker-options{height:0;flex:1 1 0;min-height:0;overflow-y:scroll;scrollbar-gutter:stable;scrollbar-width:thin;scrollbar-color:#91afa3 #edf4f0}.sku-picker-options::-webkit-scrollbar{width:10px}.sku-picker-options::-webkit-scrollbar-track{background:#edf4f0;border-left:1px solid #dce9e2}.sku-picker-options::-webkit-scrollbar-thumb{background:#91afa3;border:2px solid #edf4f0;border-radius:999px}.sku-picker-options::-webkit-scrollbar-thumb:hover{background:#5e8978}.sku-picker-options label{display:grid;grid-template-columns:18px minmax(0,1fr) auto;gap:8px;align-items:center;padding:8px 11px;cursor:pointer;border-bottom:1px solid #f0f4f1}.sku-picker-options label:hover,.sku-picker-options label.active{background:#eff8f4}.sku-picker-options input{margin:0}.sku-picker-options b,.sku-picker-options small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.sku-picker-options b{font-size:var(--text-body);color:#23473d}.sku-picker-options small{margin-top:2px;color:#81908a;font-size:var(--text-caption)}.sku-picker-options .sku-identifiers{display:flex;gap:12px}.sku-picker-options .sku-identifiers span{min-width:0;overflow:hidden;text-overflow:ellipsis}.sku-picker-options em{white-space:nowrap;font-style:normal;color:#436d60;font-size:var(--text-body)}.sku-picker-options p,.sku-picker-preview>p{margin:0;padding:18px;color:#81908a;font-size:var(--text-body)}.sku-picker-preview{padding:14px;background:#f7fbf9}.sku-picker-preview>small{display:block;color:#799087;font-size:var(--text-caption)}.sku-picker-preview>strong{display:block;margin:4px 0 10px;color:#1d4d40;font-size:var(--text-section)}.sku-picker-preview dl{margin:0 0 11px}.sku-picker-preview dl div{display:grid;grid-template-columns:105px 1fr;gap:8px;margin-top:5px;font-size:var(--text-body)}.sku-picker-preview dt{color:#7a8983}.sku-picker-preview dd{min-width:0;overflow-wrap:anywhere;margin:0;color:#38564d}.sku-picker-preview :deep(label){display:block;color:#526d64;font-size:var(--text-body)}.sku-picker-preview :deep(textarea){display:block;width:100%;min-height:54px;margin-top:5px;border:1px solid #b8d3c7;border-radius:7px;padding:7px;resize:vertical;font:inherit;font-size:var(--text-body)}@media(max-width:720px){.sku-selection-panel{grid-template-columns:1fr}.sku-picker-list{border-right:0;border-bottom:1px solid #e4ece7}}@media(max-width:560px){.sku-picker-filters{grid-template-columns:1fr}.sku-picker-options .sku-identifiers{display:block}.sku-picker-options .sku-identifiers span{display:block}}
@media(max-width:720px){.sku-selection-panel{height:auto;min-height:var(--sku-picker-height);align-content:start}.sku-picker-options{height:auto;min-height:160px;max-height:260px;overflow-y:auto}.sku-picker-preview{min-height:132px}}
</style>
