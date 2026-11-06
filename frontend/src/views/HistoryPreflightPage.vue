<script setup>
import { computed, ref } from 'vue'
import { AlertTriangle, ArrowRight, CircleHelp, Download, FileUp } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import { api } from '../api'

const fileInput = ref(null)
const file = ref(null)
const preview = ref(null)
const previewFile = ref(null)
const loading = ref(false)
const downloading = ref(false)
const error = ref('')
const showPassedRows = ref(false)
let selectionVersion = 0

const summary = computed(() => preview.value?.summary || {})
const issueRows = computed(() => (preview.value?.results || []).filter(row => row.status !== '通过'))
const visibleRows = computed(() => showPassedRows.value ? (preview.value?.results || []) : issueRows.value)

function chooseFile(event) {
  selectionVersion += 1
  file.value = event.target.files?.[0] || null
  preview.value = null
  previewFile.value = null
  error.value = ''
  loading.value = false
  downloading.value = false
  showPassedRows.value = false
}

function fileSize(bytes) {
  if (!Number.isFinite(bytes)) return ''
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formData(workbook) {
  const body = new FormData()
  body.append('file', workbook)
  return body
}

async function runPreflight() {
  if (!file.value || loading.value) return
  const workbook = file.value
  const version = selectionVersion
  loading.value = true
  error.value = ''
  preview.value = null
  previewFile.value = null
  showPassedRows.value = false
  try {
    const response = await api.post('/import/history-preflight/', formData(workbook))
    if (version !== selectionVersion || file.value !== workbook) return
    preview.value = response.data
    previewFile.value = workbook
  } catch (e) {
    if (version === selectionVersion && file.value === workbook) {
      error.value = e.message || '预检失败，请检查文件后重试。'
    }
  } finally {
    if (version === selectionVersion && file.value === workbook) loading.value = false
  }
}

async function downloadCsv() {
  const workbook = previewFile.value
  if (!workbook || workbook !== file.value || !preview.value || downloading.value) return
  const version = selectionVersion
  downloading.value = true
  error.value = ''
  try {
    const response = await api.post('/import/history-preflight/?report=csv', formData(workbook), { responseType: 'blob' })
    if (version !== selectionVersion || file.value !== workbook || previewFile.value !== workbook) return
    const url = URL.createObjectURL(response.data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'history-preflight.csv'
    document.body.appendChild(anchor)
    anchor.click()
    setTimeout(() => {
      anchor.remove()
      URL.revokeObjectURL(url)
    }, 1000)
  } catch (e) {
    if (version === selectionVersion && file.value === workbook && previewFile.value === workbook) {
      error.value = e.message || 'CSV 下载失败，请重试。'
    }
  } finally {
    if (version === selectionVersion) downloading.value = false
  }
}

function statusClass(status) {
  return ({ 通过: 'passed', 警告: 'warning', 待人工核实: 'review', 阻断: 'blocked' })[status] || 'unknown'
}
</script>

<template>
  <main class="history-preflight-page">
    <header class="preflight-intro">
      <div>
        <p class="preflight-eyebrow">只读检查</p>
        <h2>历史资料预检</h2>
        <p>上传 .xlsx 文件查看检查结果，按需下载问题清单。</p>
      </div>
      <RouterLink class="preflight-takeover-link" to="/history-takeover">
        <span>需要提交承接申请？</span><strong>进入历史资料承接</strong><ArrowRight :size="16" />
      </RouterLink>
    </header>

    <section class="preflight-upload panel" aria-labelledby="preflight-upload-title">
      <div class="preflight-section-title">
        <div><h3 id="preflight-upload-title"><FileUp :size="18" />选择工作簿</h3><p>请选择 .xlsx 文件，文件大小需符合系统限制。</p></div>
      </div>
      <div class="preflight-upload-row">
        <label class="preflight-file">
          <span class="preflight-file-name">{{ file?.name || '请选择历史资料工作簿' }}</span>
          <small v-if="file">{{ fileSize(file.size) }}</small>
          <input ref="fileInput" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" @change="chooseFile" />
        </label>
        <button class="preflight-primary" type="button" :disabled="!file || loading" @click="runPreflight">
          {{ loading ? '正在预检…' : '开始预检' }}
        </button>
      </div>
      <p class="preflight-notice"><CircleHelp :size="16" />预检只读取工作簿和现有资料，不创建承接申请，也不修改库存、应收应付、订单或私有媒体。预检通过后，仍需提交申请并通过审核，才能承接。</p>
    </section>

    <section v-if="error" class="preflight-error" role="alert"><AlertTriangle :size="18" /><span>{{ error }}</span></section>

    <template v-if="preview && previewFile === file">
      <section class="preflight-summary panel" aria-labelledby="preflight-summary-title">
        <div class="preflight-section-title">
          <div><h3 id="preflight-summary-title">预检汇总</h3><p>{{ previewFile?.name }}</p></div>
          <button class="preflight-secondary" type="button" :disabled="downloading" @click="downloadCsv">
            <Download :size="16" />{{ downloading ? '正在准备 CSV…' : '下载 CSV 清单' }}
          </button>
        </div>
        <div class="preflight-summary-grid">
          <div class="preflight-overall"><span>总体结果</span><strong :class="`status-${statusClass(summary.overall_status)}`">{{ summary.overall_status || '—' }}</strong></div>
          <div><span>数据行</span><strong>{{ summary.total_rows ?? 0 }}</strong></div>
          <div><span>通过</span><strong>{{ summary.passed ?? 0 }}</strong></div>
          <div><span>警告</span><strong>{{ summary.warnings ?? 0 }}</strong></div>
          <div><span>待人工核实</span><strong>{{ summary.manual_review ?? 0 }}</strong></div>
          <div><span>阻断</span><strong>{{ summary.blocked ?? 0 }}</strong></div>
        </div>
        <p v-if="preview.notice" class="preflight-preview-notice">{{ preview.notice }}</p>
      </section>

      <section class="preflight-results panel" aria-labelledby="preflight-results-title">
        <div class="preflight-section-title">
          <div><h3 id="preflight-results-title">行级问题</h3><p>显示 {{ showPassedRows ? visibleRows.length : issueRows.length }} 行{{ showPassedRows ? '' : '问题记录' }} / 共 {{ summary.total_rows ?? 0 }} 行</p></div>
          <button class="preflight-text-button" type="button" @click="showPassedRows = !showPassedRows">
            {{ showPassedRows ? '仅看问题行' : '查看全部行' }}
          </button>
        </div>
        <p v-if="!visibleRows.length" class="preflight-empty">{{ showPassedRows ? '没有可显示的预检结果。' : '本次预检未发现需要处理的问题。' }}</p>
        <div v-else class="preflight-table-wrap">
          <table class="preflight-table">
            <thead><tr><th>工作表</th><th>原行号</th><th>原系统记录编号</th><th>来源关联组编号</th><th>结果</th><th>原因</th><th>建议处理方式</th></tr></thead>
            <tbody>
              <tr v-for="(row, index) in visibleRows" :key="`${row.sheet}-${row.row}-${index}`">
                <td>{{ row.sheet }}</td><td>{{ row.row }}</td>
                <td class="preflight-source-id">{{ row.source_record_id || '—' }}</td>
                <td>{{ row.group_id || '—' }}</td>
                <td><span class="preflight-status" :class="`status-${statusClass(row.status)}`">{{ row.status }}</span></td>
                <td><ul v-if="row.reasons?.length"><li v-for="(reason, reasonIndex) in row.reasons" :key="reasonIndex">{{ reason.message }}</li></ul><span v-else>—</span></td>
                <td><ul v-if="row.suggested_actions?.length"><li v-for="(action, actionIndex) in row.suggested_actions" :key="actionIndex">{{ action }}</li></ul><span v-else>—</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.history-preflight-page{display:grid;gap:16px;min-width:0;color:#243b33}
.preflight-intro,.preflight-upload,.preflight-summary,.preflight-results{min-width:0;padding:20px;border:1px solid #dfe7e2;border-radius:13px;background:#fff}
.preflight-intro{display:flex;justify-content:space-between;align-items:flex-start;gap:18px}
.preflight-intro h2{margin:0;font-size:22px}.preflight-intro p:not(.preflight-eyebrow){margin:6px 0 0;color:#6c7d74}
.preflight-eyebrow{margin:0 0 5px;color:#788b80;font-size:12px;letter-spacing:.06em}
.preflight-takeover-link{display:flex;align-items:center;gap:7px;flex-wrap:wrap;padding:9px 11px;border:1px solid #dce7df;border-radius:9px;background:#f7faf8;color:#315c4a;font-size:13px;text-decoration:none}
.preflight-takeover-link span{color:#708078}.preflight-takeover-link:hover{border-color:#a7c5b4;background:#eff6f1}
.preflight-section-title{display:flex;justify-content:space-between;align-items:center;gap:14px}.preflight-section-title h3{display:flex;align-items:center;gap:8px;margin:0;font-size:16px}.preflight-section-title p{margin:5px 0 0;color:#74847c;font-size:13px}
.preflight-upload-row{display:flex;align-items:stretch;gap:10px;margin-top:14px}
.preflight-file{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:4px 12px;flex:1;min-width:0;padding:10px 12px;border:1px dashed #a8beb2;border-radius:8px;color:#566d61}
.preflight-file-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.preflight-file small{color:#7a8981;font-size:11px}.preflight-file input{grid-column:1/-1;width:100%;font-size:12px}
.preflight-primary,.preflight-secondary,.preflight-text-button{display:inline-flex;align-items:center;justify-content:center;gap:7px;border:1px solid #1c5c4c;border-radius:8px;padding:9px 13px;background:#1c5c4c;color:#fff;font-weight:700;cursor:pointer}
.preflight-secondary{flex:none;border-color:#cddbd3;background:#fff;color:#315c4a}.preflight-text-button{border:0;background:transparent;color:#456b5a;padding:8px}.preflight-primary:disabled,.preflight-secondary:disabled{opacity:.55;cursor:not-allowed}
.preflight-notice{display:flex;align-items:flex-start;gap:7px;margin:12px 0 0;padding:10px 12px;border-radius:8px;background:#f1f6f3;color:#4c6d5b;font-size:13px;line-height:1.6}.preflight-notice svg{flex:none;margin-top:2px}
.preflight-error{display:flex;align-items:flex-start;gap:8px;padding:11px 13px;border:1px solid #e8c2b9;border-radius:8px;background:#fff7f5;color:#8b3b30;overflow-wrap:anywhere}.preflight-error svg{flex:none;margin-top:2px}
.preflight-summary-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin-top:16px}.preflight-summary-grid>div{padding:10px 11px;border:1px solid #e7ede9;border-radius:8px;color:#708078;font-size:12px}.preflight-summary-grid strong{display:block;margin-top:3px;color:#244c3a;font-size:18px}.preflight-summary-grid .preflight-overall strong{font-size:15px}.preflight-summary-grid .status-blocked{color:#a33c35}.preflight-summary-grid .status-review{color:#9a641c}.preflight-summary-grid .status-warning{color:#7b651b}.preflight-preview-notice{margin:12px 0 0;color:#728279;font-size:12px;line-height:1.6}
.preflight-results .preflight-section-title{margin-bottom:12px}.preflight-empty{padding:20px;border-radius:8px;background:#f7faf8;color:#718078;text-align:center}.preflight-table-wrap{max-height:70vh;overflow:auto;border:1px solid #e7ede9;border-radius:8px}.preflight-table{width:100%;min-width:980px;border-collapse:collapse}.preflight-table th{position:sticky;top:0;z-index:1;padding:10px 12px;background:#f6f9f7;color:#64766d;text-align:left;font-size:12px;white-space:nowrap}.preflight-table td{max-width:380px;padding:10px 12px;border-top:1px solid #edf0ed;color:#43504c;font-size:13px;vertical-align:top;overflow-wrap:anywhere}.preflight-table ul{display:grid;gap:4px;margin:0;padding-left:17px}.preflight-source-id{font-weight:600;color:#2e4c3d}.preflight-status{display:inline-flex;padding:3px 7px;border-radius:999px;background:#edf5ef;color:#37604b;font-size:12px;white-space:nowrap}.preflight-status.status-warning{background:#fff8e8;color:#846314}.preflight-status.status-review{background:#fff3df;color:#8b5815}.preflight-status.status-blocked{background:#fff0ed;color:#9a3e34}
@media(max-width:1000px){.preflight-summary-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:600px){.preflight-intro,.preflight-upload,.preflight-summary,.preflight-results{padding:15px}.preflight-intro{display:grid}.preflight-takeover-link{width:100%}.preflight-upload-row{display:grid}.preflight-primary{min-height:42px}.preflight-section-title{align-items:flex-start}.preflight-summary-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.preflight-summary-grid .preflight-overall{grid-column:1/-1}.preflight-results .preflight-section-title{flex-wrap:wrap}.preflight-table-wrap{max-height:65vh}}
</style>
