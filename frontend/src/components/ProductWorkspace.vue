<script setup>
import { computed, ref, watch } from 'vue'
import ProductSalesRules from './ProductSalesRules.vue'
import ProductSkuManagement from './ProductSkuManagement.vue'
import { Boxes, FileText, ChevronRight, Plus } from 'lucide-vue-next'
const props = defineProps({ data: Object, activeTab: String, productId: [Number, String] })
const emit = defineEmits(['update:activeTab', 'drill', 'createSku', 'changed'])
const refreshKey = ref(0)
watch(() => props.data, () => { refreshKey.value += 1 })
const search = ref(''), start = ref(''), end = ref(''), currency = ref(''), unit = ref('')
const section = key => props.data.sections.find(item => item.key === key)
const rows = key => section(key)?.rows || []
const navigate = key => emit('update:activeTab', key)
const tabs = computed(() => ['skus', 'suppliers', 'sales', 'sales-summary', 'inventory', 'parameters', 'certificates'].map(key => section(key)).filter(Boolean))
const sales = computed(() => rows('sales'))
const currencies = computed(() => [...new Set(sales.value.map(row => row.currency))].filter(Boolean))
const units = computed(() => [...new Set(sales.value.map(row => row.unit))].filter(Boolean))
const chosenCurrency = computed(() => currency.value || currencies.value[0] || '')
const chosenUnit = computed(() => unit.value || units.value[0] || '')
const filteredSales = computed(() => sales.value.filter(row => (!start.value || row.order_date >= start.value) && (!end.value || row.order_date <= end.value) && (!chosenCurrency.value || row.currency === chosenCurrency.value) && (!chosenUnit.value || row.unit === chosenUnit.value) && [row.order_no, row.customer_name, row.sales_model, row.sku_code].some(value => String(value || '').toLowerCase().includes(search.value.toLowerCase()))))
const amount = computed(() => filteredSales.value.reduce((sum, row) => sum + Number(row.amount || 0), 0))
const quantity = computed(() => filteredSales.value.reduce((sum, row) => sum + Number(row.quantity || 0), 0))
const groups = field => {
 const map = new Map()
 filteredSales.value.forEach(row => { const key = field === 'month' ? String(row.order_date).slice(0,7) : row[field] || '未填写'; map.set(key, (map.get(key) || 0) + Number(field === 'sales_model' ? row.quantity : row.amount)) })
 return [...map].map(([label,value]) => ({label,value})).sort((a,b) => field === 'month' ? a.label.localeCompare(b.label) : b.value-a.value)
}
const months = computed(() => groups('month'))
const ranking = computed(() => groups('sales_model').slice(0,6))
const customers = computed(() => groups('customer_name').slice(0,6))
const number = value => Number(value || 0).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
const width = (value, list) => `${Math.max(0, value / Math.max(1,...list.map(row => row.value)) * 100)}%`
function reset() { search.value=''; start.value=''; end.value=''; currency.value=''; unit.value='' }
</script>

<template>
 <div class="product-workspace">
  <nav class="product-tabs" aria-label="产品详情导航">
   <button :class="{active:activeTab==='__overview'}" @click="navigate('__overview')">总览</button>
   <button v-for="tab in tabs" :key="tab.key" :class="{active:activeTab===tab.key}" @click="navigate(tab.key)">{{ tab.key==='skus' ? 'SKU 管理' : tab.key==='suppliers' ? '供应能力规则' : tab.title }}<span v-if="tab.key!=='sales-summary'">{{ tab.rows.length }}</span></button>
   <button :class="{active:activeTab==='sales-rules'}" @click="navigate('sales-rules')">销售规则</button>
   <button :class="{active:activeTab==='__operation_logs'}" @click="navigate('__operation_logs')">操作日志</button>
  </nav>
  <main class="workspace-content">
   <template v-if="activeTab==='__overview'">
    <section class="workspace-card"><h3><FileText :size="18"/>基础信息</h3><dl class="product-info"><div v-for="item in data.info" :key="item[0]"><dt>{{ item[0] }}</dt><dd>{{ item[1] }}</dd></div></dl></section>
    <div class="preview-grid"><section v-for="key in ['suppliers','skus','inventory']" :key="key" class="workspace-card"><div class="card-title"><h3>{{ section(key)?.title }}预览</h3><button @click="navigate(key)">查看全部 <ChevronRight :size="14"/></button></div><button class="preview-row" v-for="(row,index) in rows(key).slice(0,4)" :key="index" @click="emit('drill',row)"><div><strong>{{ row.name || row.sales_model || row.movement_no || row.sku }}</strong><small>{{ row.main_products || row.display_name_cn || row.type_display || '—' }}</small></div><ChevronRight :size="16"/></button><p v-if="!rows(key).length" class="empty">暂无关联记录</p></section></div>
   </template>
   <template v-else-if="activeTab==='sales-summary' || activeTab==='sales'">
    <section class="workspace-card"><h3>筛选条件</h3><div class="sales-filters"><label>开始日期<input type="date" v-model="start"/></label><label>结束日期<input type="date" v-model="end" :min="start"/></label><label>币种<select v-model="currency"><option value="">{{ currencies[0] || '暂无币种' }}</option><option v-for="item in currencies" :key="item" :value="item">{{ item }}</option></select></label><label>单位<select v-model="unit"><option value="">{{ units[0] || '暂无单位' }}</option><option v-for="item in units" :key="item" :value="item">{{ item }}</option></select></label><label class="keyword">关键词<input v-model="search" placeholder="订单、客户、SKU 或销售型号"/></label><button @click="reset">重置</button></div><p class="subtle">按产品订单明细统计，排除已取消订单；不同币种和单位分别查看。</p></section>
    <template v-if="activeTab==='sales-summary'">
     <div class="sales-metrics"><section class="workspace-card"><small>所选范围订单数</small><strong>{{ new Set(filteredSales.map(row=>row.order_no)).size }}</strong></section><section class="workspace-card"><small>订购数量 · {{ chosenUnit || '—' }}</small><strong>{{ number(quantity) }}</strong></section><section class="workspace-card"><small>订单金额 · {{ chosenCurrency || '—' }}</small><strong>{{ number(amount) }}</strong></section></div>
     <div class="chart-grid"><section class="workspace-card"><h3>月度订单金额 · {{ chosenCurrency }}</h3><div v-for="item in months" :key="item.label" class="bar-row"><span>{{ item.label }}</span><div><i :style="{width:width(item.value,months)}"/></div><b>{{ number(item.value) }}</b></div><p v-if="!months.length" class="empty">所选范围暂无销售数据</p></section><section class="workspace-card"><h3>SKU 订购数量排行 · {{ chosenUnit }}</h3><div v-for="item in ranking" :key="item.label" class="rank-row"><span>{{ item.label }}</span><b>{{ number(item.value) }}</b><div><i :style="{width:width(item.value,ranking)}"/></div></div><p v-if="!ranking.length" class="empty">暂无 SKU 销售记录</p></section><section class="workspace-card"><h3>客户订单金额 · {{ chosenCurrency }}</h3><div v-for="item in customers" :key="item.label" class="rank-row"><span>{{ item.label }}</span><b>{{ number(item.value) }}</b><div><i :style="{width:width(item.value,customers)}"/></div></div><p v-if="!customers.length" class="empty">暂无客户销售记录</p></section></div>
    </template>
    <section class="workspace-card"><div class="card-title"><h3>{{ activeTab==='sales' ? '订单记录' : '销售明细' }}</h3><span>{{ filteredSales.length }} 条明细</span></div><div class="sales-table"><table><thead><tr><th>日期</th><th>订单</th><th>客户</th><th>销售型号</th><th>数量</th><th>金额</th><th>状态</th><th></th></tr></thead><tbody><tr v-for="(row,index) in filteredSales" :key="index"><td>{{ row.order_date }}</td><td>{{ row.order_no }}</td><td>{{ row.customer_name }}</td><td>{{ row.sales_model || row.sku_code }}</td><td>{{ number(row.quantity) }} {{ row.unit }}</td><td>{{ number(row.amount) }} {{ row.currency }}</td><td>{{ row.status_label || '—' }}</td><td><button @click="emit('drill',row)">查看</button></td></tr></tbody></table><p v-if="!filteredSales.length" class="empty">没有符合条件的订单明细</p></div></section>
    <section v-if="activeTab==='sales'" class="workspace-card"><div class="card-title"><h3>产品出入库流水</h3><button @click="navigate('inventory')">查看全部 <ChevronRight :size="14"/></button></div><button v-for="row in rows('inventory').slice(0,5)" :key="row.id" class="preview-row" @click="emit('drill',row)"><span>{{ row.movement_no }} · {{ row.type_display }}</span><span>{{ row.signed_quantity }} · {{ row.movement_date }}</span></button><p v-if="!rows('inventory').length" class="empty">暂无出入库记录</p></section>
   </template>
   <ProductSalesRules v-else-if="activeTab==='sales-rules'" :product-id="productId" />
   <template v-else-if="activeTab==='suppliers'"><ProductSkuManagement :product-id="productId" :refresh-key="refreshKey" initial-tab="rules" @drill="emit('drill', $event)" @changed="emit('changed')" /></template>
   <template v-else><section v-if="activeTab==='skus'" class="workspace-card matrix-intro"><div><h3><Boxes :size="20"/>SKU 管理与批量维护</h3><p class="subtle">新增组合在上方填写；下方统一维护已有 SKU、候选供应商及启停状态。</p></div><button class="primary" @click="emit('createSku')"><Plus :size="17"/>新增 SKU 组合</button></section><slot/><ProductSkuManagement v-if="activeTab==='skus'" :product-id="productId" :refresh-key="refreshKey" initial-tab="suppliers" @drill="emit('drill', $event)" @changed="emit('changed')" /></template>
  </main>
 </div>
</template>

<style scoped>
.product-workspace{color:#203b34;background:#f4f8f6}.product-tabs{position:sticky;top:0;z-index:5;display:flex;overflow:auto;gap:12px;padding:0 28px;background:#fff;border-bottom:1px solid #dbe7e1}.product-tabs button{flex:none;padding:17px 13px;border:0;border-bottom:3px solid transparent;background:transparent;color:#62756d;font-weight:600}.product-tabs button.active{color:#096351;border-bottom-color:#096351}.product-tabs span{margin-left:8px;border-radius:14px;background:#edf2ef;padding:2px 6px;font-size:var(--text-body)}.workspace-content{padding:22px 28px;display:grid;gap:16px}.workspace-card{background:white;border:1px solid #dce7e1;border-radius:11px;padding:19px;min-width:0}.workspace-card h3{display:flex;align-items:center;gap:9px;margin:0 0 16px;font-size:var(--text-section);color:#152f28}.workspace-card h3 svg{color:#117761}.product-info{display:grid;grid-template-columns:1fr 1fr;gap:15px 40px;margin:0}.product-info>div{display:grid;grid-template-columns:90px 1fr;gap:10px;font-size:var(--text-body)}.product-info dt{color:#7c8984}.product-info dd{margin:0;overflow-wrap:anywhere;white-space:pre-wrap}.workspace-content button{cursor:pointer;font-family:inherit}.sales-filters button,.matrix-intro>button{display:flex;align-items:center;justify-content:center;gap:8px;border:1px solid #d4e2da;border-radius:6px;background:#fff;color:#285d4e;padding:11px 14px}.preview-grid,.chart-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.card-title{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:10px}.card-title h3{margin:0}.card-title button,.sales-table button{border:0;background:transparent;color:#16755c;display:flex;align-items:center;gap:4px}.card-title>span,.subtle{font-size:var(--text-caption);color:#7e8e85}.preview-row{width:100%;display:flex;align-items:center;justify-content:space-between;gap:8px;padding:13px 0;border:0;border-bottom:1px solid #edf2ef;background:#fff;text-align:left;color:#315647;font-size:var(--text-body)}.preview-row strong,.preview-row small{display:block;overflow-wrap:anywhere}.preview-row small{color:#819288;margin-top:5px}.empty{text-align:center;padding:24px;color:#819288;font-size:var(--text-body)}.sales-filters{display:flex;align-items:end;gap:12px;flex-wrap:wrap}.sales-filters label{display:grid;gap:8px;font-size:var(--text-caption);color:#71857a}.sales-filters input,.sales-filters select{padding:9px;border:1px solid #d4e2da;border-radius:6px;background:#fff;color:#294e3e;min-width:90px}.keyword{flex:1}.sales-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.sales-metrics small{color:#799082}.sales-metrics strong{display:block;font-size:var(--text-metric);margin-top:10px}.bar-row{display:grid;grid-template-columns:60px 1fr 60px;align-items:center;gap:8px;font-size:var(--text-caption);margin-top:18px}.bar-row>div,.rank-row>div{height:9px;border-radius:3px;background:#e9f1ec;overflow:hidden}.bar-row i,.rank-row i{display:block;height:100%;background:linear-gradient(90deg,#0b7158,#64b7a1)}.rank-row{display:grid;grid-template-columns:1fr auto;gap:8px;font-size:var(--text-caption);margin-top:16px}.rank-row>span{overflow-wrap:anywhere}.rank-row>div{grid-column:1/-1}.sales-table{overflow:auto}.sales-table table{width:100%;border-collapse:collapse;white-space:nowrap;font-size:var(--text-caption)}.sales-table th{background:#f2f7f4;color:#75887e;text-align:left;padding:12px}.sales-table td{padding:12px;border-bottom:1px solid #eaf0ec}.matrix-intro{display:flex;justify-content:space-between;align-items:center;gap:20px}.matrix-intro h3{margin-bottom:8px}.matrix-intro .primary{background:#11634f;color:#fff;white-space:nowrap}button:focus-visible{outline:2px solid #258870;outline-offset:3px}@media(max-width:1100px){.preview-grid,.chart-grid{grid-template-columns:1fr}.product-info{grid-template-columns:1fr}}@media(max-width:650px){.workspace-content{padding:12px}.product-tabs{padding:0 12px;gap:0}.sales-metrics{grid-template-columns:1fr}.matrix-intro{align-items:stretch;flex-direction:column}}
</style>
