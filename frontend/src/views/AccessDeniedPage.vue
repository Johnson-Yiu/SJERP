<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { accessState, firstPermittedPath, loadAccessControl } from '../accessControl'

const route = useRoute()
const router = useRouter()
const failed = computed(() => route.name === 'access-status-error' || Boolean(accessState.error))
const returnPath = computed(() => firstPermittedPath())
async function retry() {
  try { await loadAccessControl({ force: true }) } catch { /* 错误状态留在当前页 */ }
  if (returnPath.value) await router.replace(returnPath.value)
}
</script>

<template>
  <section class="access-denied panel" role="alert">
    <div class="access-denied-mark">403</div>
    <h2>{{ failed ? '权限状态暂不可用' : '无权访问此功能' }}</h2>
    <p>{{ failed ? '系统未能读取当前账号的权限，请重新加载权限状态后再试。' : '当前账号没有查看此页面的权限。' }}</p>
    <small v-if="failed && accessState.error">{{ accessState.error }}</small>
    <div class="access-denied-actions">
      <button v-if="failed" class="btn btn-secondary" type="button" @click="retry">重新检查</button>
      <RouterLink v-if="returnPath" class="btn btn-primary" :to="returnPath">返回可访问页面</RouterLink>
    </div>
  </section>
</template>

<style scoped>
.access-denied{max-width:560px;margin:clamp(40px,12vh,120px) auto;padding:36px;text-align:center}.access-denied-mark{display:grid;place-items:center;width:56px;height:56px;margin:0 auto 14px;border-radius:16px;background:#fff2e8;color:#a85724;font-size:18px;font-weight:800}.access-denied h2{margin:0;color:#24483e;font-size:22px}.access-denied p{margin:9px 0;color:#71817b}.access-denied small{display:block;color:#a44343;overflow-wrap:anywhere}.access-denied-actions{display:flex;justify-content:center;gap:9px;margin-top:20px}
</style>
