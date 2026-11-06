<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { loadAccessControl } from '../accessControl'
import { safeReturn } from '../utils/safeReturn'

const route = useRoute(), router = useRouter()
const username = ref(''), password = ref(''), busy = ref(false), error = ref('')
async function submit() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try {
    await api.get('/session/csrf/')
    await api.post('/session/login/', { username: username.value, password: password.value })
    password.value = ''
    await loadAccessControl({ force: true })
    await router.replace(safeReturn(route.query.next, window.location.origin))
  } catch (failure) {
    password.value = ''
    error.value = failure?.status === 400 ? '账号或密码不正确，请重试。' : '登录未完成，请检查网络后重试。'
  } finally { busy.value = false }
}
</script>

<template>
  <main class="login-page"><form class="login-card" @submit.prevent="submit">
    <h1>登录森爵管理系统</h1><p v-if="route.query.reason === 'expired'">登录已过期，请重新登录。</p><p v-else>请输入分配给你的账号。</p>
    <label>账号<input v-model="username" autocomplete="username" required /></label>
    <label>密码<input v-model="password" type="password" autocomplete="current-password" required /></label>
    <p v-if="error" role="alert">{{ error }}</p>
    <button type="submit" :disabled="busy">{{ busy ? '登录中…' : '登录' }}</button>
  </form></main>
</template>

<style scoped>
.login-page{min-height:100vh;display:grid;place-items:center;padding:24px;background:#f3f7f4}.login-card{width:min(100%,400px);padding:28px;background:white;border-radius:16px;box-shadow:0 8px 35px #163b3020}.login-card h1{font-size:24px}.login-card p{color:#52635b}.login-card label{display:grid;gap:6px;margin:18px 0}.login-card input{width:100%;padding:11px;border:1px solid #b8c9bf;border-radius:7px;font:inherit}.login-card button{width:100%;padding:12px;background:#194c3c;color:white;border:0;border-radius:7px;font:inherit}.login-card [role=alert]{color:#a62b2b}
</style>
