<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { accessState, firstPermittedPath, loadAccessControl } from '../accessControl'

const route = useRoute(), router = useRouter()
const retrying = ref(false), retryError = ref(''), checked = ref(false)
// A permission denial and a failed permission lookup are distinct route outcomes.
const failed = computed(() => route.name === 'access-status-error')
const returnPath = computed(() => {
  const path = firstPermittedPath()
  return path && !['/access-denied', '/access-status-error'].includes(path) ? path : ''
})
const reason = computed(() => retryError.value || (failed.value ? accessState.error : ''))
async function retry() {
  if (retrying.value || accessState.loading) return
  retrying.value = true; retryError.value = ''; checked.value = false
  try {
    await loadAccessControl({ force: true })
    checked.value = true
    if (returnPath.value) await router.replace(returnPath.value)
  } catch (e) {
    retryError.value = e?.response?.status === 401 ? '当前会话未被识别，请重新检查权限状态。' : e?.response?.status === 403 ? '服务端拒绝读取权限状态，请联系权限管理员核对。' : e.message || '权限状态服务暂不可用，请稍后重试。'
  } finally { retrying.value = false }
}
</script>

<template>
  <section class="access-denied panel" :aria-busy="retrying" aria-labelledby="access-state-title">
    <div class="access-denied-mark" aria-hidden="true">{{ failed ? '!' : '403' }}</div>
    <h2 id="access-state-title">{{ failed ? '权限状态获取失败' : '没有此页面的访问权限' }}</h2>
    <p>{{ failed ? '暂时无法确认当前身份的权限。请重新加载权限状态，再继续操作。' : '当前身份没有查看此页面的权限。可返回其他页面，或请权限管理员核对角色配置。' }}</p>
    <div v-if="reason" class="access-error" role="alert"><strong>错误信息</strong><p>{{ reason }}</p></div>
    <p v-if="checked && !returnPath" class="access-empty" role="status">权限状态已读取，但当前没有可访问的业务页面。请联系权限管理员。</p>
    <p v-else-if="!returnPath && !failed" class="access-empty">当前没有可返回的业务页面，可重新加载权限状态。</p>
    <p v-if="retrying" role="status">正在重新加载权限状态…</p>
    <div class="access-denied-actions"><button class="btn btn-secondary" type="button" :disabled="retrying || accessState.loading" @click="retry">{{ retrying ? '正在检查…' : '重新加载权限状态' }}</button><RouterLink v-if="returnPath && !retrying" class="btn btn-primary" :to="returnPath">返回可访问页面</RouterLink></div>
    <small>重新加载只检查当前权限，不会修改角色配置。</small>
  </section>
</template>

<style scoped>
.access-denied{box-sizing:border-box;width:100%;max-width:680px;min-width:0;margin:clamp(30px,8vh,90px) auto;padding:32px;text-align:center;overflow-wrap:anywhere}.access-denied-mark{display:grid;place-items:center;width:56px;height:56px;margin:0 auto 16px;border-radius:16px;background:#fff2e8;color:#a85724;font-size:22px;font-weight:800}.access-denied h2{margin:0;color:#24483e;font-size:var(--text-page);line-height:1.5}.access-denied p{margin:12px 0;color:#64786e;line-height:1.8}.access-error{text-align:left;border:1px solid #e6c9c3;background:#fff7f4;border-radius:8px;padding:14px;margin-top:18px;color:#963e33;max-height:260px;overflow:auto}.access-error p{margin:6px 0 0;color:inherit;white-space:pre-wrap}.access-denied-actions{display:flex;justify-content:center;flex-wrap:wrap;gap:10px;margin:22px 0 18px}.access-denied small{display:block;color:#82918a;line-height:1.7}.access-empty{padding:10px;background:#f4f7f4;border-radius:8px}.access-denied button:disabled{opacity:.6;cursor:not-allowed}@media(max-width:650px){.access-denied{padding:22px;margin:24px auto}.access-denied-actions{flex-direction:column;align-items:stretch}}
</style>
