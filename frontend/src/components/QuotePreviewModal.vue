<script setup>
import { computed } from 'vue'
import { Printer, X } from 'lucide-vue-next'
import { formatPiAmountWords } from '../utils/piAmountWords'
import { useAccessControl } from '../accessControl'

const props = defineProps({ draft: { type: Object, required: true }, saved: { type: Boolean, default: false } })
defineEmits(['close'])
const { can } = useAccessControl()

const seller = Object.freeze({
  name: 'Guangzhou Sunjack Lighting Co., Ltd.',
  saler: 'Johnson',
  address: 'C0615, Room 201, 1411 Huaguan Road, Guangzhou City, China',
  email: 'johnsonyao@sunjack.cn',
  phone: '+86-18103040544',
})

const bankRows = Object.freeze([
  ['Beneficiary Name', 'Guangzhou Sunjack Lighting Co., Ltd.'],
  ['Beneficiary Account Number', '63001208199'],
  ['Swift Code', 'CHASHKHHXXX'],
  ['Country/Region', 'HongKong'],
  ['Beneficiary Address', 'Units 1260, 12/F, Emperor Group Centre, 288 Hennessy Road, Wan Chai, Hong Kong'],
  ['Beneficiary Bank', 'JPMorgan Chase Bank N.A., Hong Kong Branch'],
  ['Beneficiary Bank Address', 'CHARTER HOUSE, 8 CONNAUGHT ROAD, CENTRAL, HONG KONG'],
  ['Bank Code', '7'],
  ['Branch Code', '863'],
])

function money(value) {
  return Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const amountWords = computed(() => formatPiAmountWords(props.draft.totals?.total_amount, props.draft.currency))

const validityDays = computed(() => {
  if (!props.draft.valid_until || !props.draft.quote_date) return 30
  return Math.max(0, Math.round((new Date(props.draft.valid_until) - new Date(props.draft.quote_date)) / 86400000))
})

function printPreview() {
  window.print()
}
</script>

<template>
  <div class="modal-backdrop quote-preview-backdrop" @mousedown.self="$emit('close')">
    <section class="quote-preview-modal" role="dialog" aria-modal="true" aria-label="报价单预览">
      <header class="quote-preview-toolbar">
        <div><strong>报价单预览</strong><small>{{ saved ? '已保存报价预览' : '当前未保存内容 · 关闭后可继续编辑' }}</small></div>
        <div class="quote-preview-actions">
          <button v-if="can('quotes', 'export')" type="button" class="btn btn-secondary" @click="printPreview"><Printer :size="15" /> 导出预览 PDF</button>
          <button type="button" class="mini-btn" aria-label="关闭预览" @click="$emit('close')"><X :size="17" /></button>
        </div>
      </header>
      <div class="quote-preview-scroll">
        <article class="pi-sheet">
          <h1>Proforma Invoice</h1>
          <div class="pi-parties">
            <section>
              <h2>Buyer Information</h2>
              <dl><dt>Name</dt><dd>{{ draft.buyer.company_name || '—' }}</dd><dt>Recipient</dt><dd>{{ draft.buyer.recipient || '—' }}</dd><dt>Address</dt><dd>{{ draft.buyer.address || '—' }}</dd><dt>Tax ID</dt><dd>&nbsp;</dd><dt>Email</dt><dd>{{ draft.buyer.email || '—' }}</dd><dt>Tel</dt><dd>{{ draft.buyer.phone || '—' }}</dd></dl>
            </section>
            <section>
              <h2>Seller Information</h2>
              <dl><dt>Name</dt><dd>{{ seller.name }}</dd><dt>Saler</dt><dd>{{ seller.saler }}</dd><dt>Address</dt><dd>{{ seller.address }}</dd><dt>Email</dt><dd>{{ seller.email }}</dd><dt>Tel</dt><dd>{{ seller.phone }}</dd><dt>Date</dt><dd>{{ draft.quote_date }}</dd></dl>
            </section>
          </div>
          <div class="pi-invoice"><span>Invoice No.</span><strong>{{ draft.quote_no || '保存后自动生成' }}</strong></div>
          <div class="pi-products">
            <div class="pi-product-head"><span>No.</span><span>Product Image</span><span>Model</span><span>Product Description</span><span>Quantity</span><span>Unit</span><span>Unit Price<br />{{ draft.currency }}</span><span>Total<br />{{ draft.currency }}</span></div>
            <div v-for="(item, index) in draft.products" :key="item.key" class="pi-product-row">
              <span>{{ index + 1 }}</span>
              <span class="pi-image-frame"><img v-if="item.image_url" :src="item.image_url" :alt="item.model || item.product_name" /></span>
              <span>{{ item.model || '—' }}</span><span>{{ item.description || item.product_name || '—' }}</span><span>{{ item.quantity }}</span><span>{{ item.unit || 'pcs' }}</span><span>{{ money(item.unit_price) }}</span><span>{{ money(item.amount) }}</span>
            </div>
          </div>
          <div class="pi-totals"><div><span>Sub Total</span><strong>{{ money(draft.totals.subtotal) }}</strong></div><div><span>Shipping Cost</span><strong>{{ money(draft.totals.shipping_fee) }}</strong></div><div v-if="Number(draft.totals.discount)"><span>Discount</span><strong>-{{ money(draft.totals.discount) }}</strong></div><div class="pi-grand-total"><span>Grand Total</span><strong>{{ money(draft.totals.total_amount) }}</strong></div></div>
          <div class="pi-amount-words">{{ amountWords }}</div>
          <div class="pi-notes"><strong>NOTES:</strong><br />1. Lead time: {{ draft.terms.lead_time_days || 10 }} Days<br />2. Price Valid Date: {{ validityDays }} Days.<br />3. Payment terms:<br />{{ Math.round(draft.payment_splits.deposit_ratio * 100) }}% ({{ draft.currency }} {{ money(draft.payment_splits.deposit_amount) }}) payment in advance, {{ Math.round(draft.payment_splits.balance_ratio * 100) }}% ({{ draft.currency }} {{ money(draft.payment_splits.balance_amount) }}) balance payment should be paid before shipping<br />4. Trading terms: {{ draft.terms.trading_terms || '—' }}<br />5. Shipping details: {{ draft.terms.shipping_details || '—' }}<br />6. The price is EXCLUDE customs duties and VAT. If the goods generate the customs taxes and VAT taxes in buyer's local, the buyer should pay by themselves.<br />7. Additional notes: {{ draft.terms.notes || '—' }}</div>
          <section class="pi-bank"><h2>BANK INFORMATION</h2><dl><template v-for="row in bankRows" :key="row[0]"><dt>{{ row[0] }}</dt><dd>{{ row[1] }}</dd></template></dl><p><strong>IMPORTANT NOTICE</strong><br />We will not change the bank account information frequently! If the "Beneficiary Name" on the Proforma Invoice is not GUANGZHOU SUNJACK LIGHTING CO., LTD., please confirm with us, DO NOT PAY WITHOUT CONFIRMATION, and prevent being scammed!</p><footer>---&nbsp; END &nbsp;---</footer></section>
        </article>
      </div>
    </section>
  </div>
</template>
