<script setup>
defineProps({
  title: { type: String, default: '操作日志' },
  logs: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  enabled: { type: Boolean, default: false },
})

function dateTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }) : '—'
}
function displayValue(value) {
  if (value === undefined || value === null || value === '') return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
</script>

<template>
  <section class="operation-log-panel">
    <div class="operation-log-head">
      <div><h3>{{ title }}</h3><p>记录创建、修改、删除及业务状态变更。</p></div>
      <span>{{ enabled ? `${logs.length} 条` : '未启用' }}</span>
    </div>
    <div v-if="loading" class="operation-log-empty">正在加载操作日志…</div>
    <div v-else-if="!enabled" class="operation-log-empty">当前身份或环境未启用操作日志。</div>
    <div v-else-if="!logs.length" class="operation-log-empty">暂无操作日志。</div>
    <ol v-else class="operation-log-list">
      <li v-for="log in logs" :key="log.id">
        <i />
        <div class="operation-log-main">
          <strong>{{ log.action_display || log.action }}</strong>
          <span>{{ log.operator_name || '系统' }} · {{ dateTime(log.created_at) }}</span>
          <small v-if="log.changed_fields?.length">变更字段：{{ log.changed_fields.join('、') }}</small>
          <small v-if="log.metadata?.summary">{{ log.metadata.summary }}</small>
          <details v-if="log.changed_fields?.length" class="operation-log-detail">
            <summary>查看变更内容</summary>
            <div v-for="field in log.changed_fields" :key="field"><b>{{ field }}</b>：{{ displayValue(log.before_data?.[field]) }} → {{ displayValue(log.after_data?.[field]) }}</div>
          </details>
        </div>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.operation-log-panel{padding:19px;border:1px solid #e0e8e4;border-radius:13px;background:#fff}.operation-log-head{display:flex;align-items:start;justify-content:space-between;gap:12px;margin-bottom:12px}.operation-log-head h3{margin:0;color:#1d3f36;font-size:var(--text-section)}.operation-log-head p{margin:5px 0 0;color:#71817b;font-size:var(--text-body)}.operation-log-head>span{padding:4px 8px;border-radius:999px;background:#edf5f1;color:#4e7668;font-size:var(--text-caption);white-space:nowrap}.operation-log-empty{padding:30px 12px;color:#81908a;font-size:var(--text-body);text-align:center}.operation-log-list{display:grid;gap:0;margin:0;padding:0;list-style:none}.operation-log-list li{display:grid;grid-template-columns:14px 1fr;gap:10px;padding:12px 0;border-top:1px solid #edf1ef}.operation-log-list li>i{width:8px;height:8px;margin-top:5px;border:2px solid #6a9b8c;border-radius:50%;background:#fff}.operation-log-main{display:grid;gap:3px}.operation-log-main strong{color:#2b5346;font-size:var(--text-body)}.operation-log-main span,.operation-log-main small{color:#7a8984;font-size:var(--text-caption)}.operation-log-main small{line-height:1.45}.operation-log-detail{margin-top:4px;color:#58766b;font-size:var(--text-caption)}.operation-log-detail summary{cursor:pointer;color:#236657}.operation-log-detail div{padding-top:3px;color:#71817b;word-break:break-word}.operation-log-detail b{color:#3d5d52}
.operation-log-head{flex-wrap:wrap}
.operation-log-head>div{flex:1 1 160px;min-width:0}
.operation-log-head>span{flex-shrink:0}
</style>
