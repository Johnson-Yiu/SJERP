<script setup>
import { computed } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({ draft: { type: Object, required: true } })
defineEmits(['close'])

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

function wholeNumberWords(value) {
  if (!value) return 'ZERO'
  const ones = ['', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'TEN', 'ELEVEN', 'TWELVE', 'THIRTEEN', 'FOURTEEN', 'FIFTEEN', 'SIXTEEN', 'SEVENTEEN', 'EIGHTEEN', 'NINETEEN']
  const tens = ['', '', 'TWENTY', 'THIRTY', 'FORTY', 'FIFTY', 'SIXTY', 'SEVENTY', 'EIGHTY', 'NINETY']
  const belowThousand = (number) => {
    const words = []
    if (number >= 100) { words.push(ones[Math.floor(number / 100)], 'HUNDRED'); number %= 100 }
    if (number >= 20) { words.push(tens[Math.floor(number / 10)]); if (number % 10) words.push(ones[number % 10]) }
    else if (number) words.push(ones[number])
    return words
  }
  const words = []
  for (const [divisor, label] of [[1_000_000_000, 'BILLION'], [1_000_000, 'MILLION'], [1_000, 'THOUSAND']]) {
    if (value >= divisor) { words.push(...belowThousand(Math.floor(value / divisor)), label); value %= divisor }
  }
  words.push(...belowThousand(value))
  return words.join(' ')
}

const amountWords = computed(() => {
  const rounded = Math.round((Number(props.draft.totals.total_amount) + Number.EPSILON) * 100) / 100
  const whole = Math.floor(rounded)
  const cents = Math.round((rounded - whole) * 100)
  const currency = { USD: 'US DOLLARS', EUR: 'EUROS', GBP: 'POUNDS STERLING', CNY: 'CHINA YUAN', RMB: 'CHINA YUAN' }[props.draft.currency] || props.draft.currency
  return `SAY TOTAL ${currency} ${wholeNumberWords(whole)}${cents ? ` AND CENTS ${wholeNumberWords(cents)}` : ''} ONLY`
})

const validityDays = computed(() => {
  if (!props.draft.valid_until || !props.draft.quote_date) return 30
  return Math.max(0, Math.round((new Date(props.draft.valid_until) - new Date(props.draft.quote_date)) / 86400000))
})
</script>

<template>
  <div class="modal-backdrop quote-preview-backdrop" @mousedown.self="$emit('close')">
    <section class="quote-preview-modal" role="dialog" aria-modal="true" aria-label="报价单预览">
      <header class="quote-preview-toolbar">
        <div><strong>报价单预览</strong><small>当前未保存内容 · 关闭后可继续编辑</small></div>
        <button type="button" class="mini-btn" aria-label="关闭预览" @click="$emit('close')"><X :size="17" /></button>
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
