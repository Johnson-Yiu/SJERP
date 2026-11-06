import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles.css'
import { normalizeMoneyInput } from './utils/money'
import { workspaceAccountScope } from './workspaceSession'

function scrollStorageKey() {
  const workspace = window.history.state?.__workspace
  const account = workspaceAccountScope()
  return workspace && account !== 'standalone' ? `senju:workspace-scroll:${account}:${workspace}` : null
}
let scrollSaveTimer = null
let restoringScroll = false

const savePageScroll = (key = scrollStorageKey()) => {
  if (restoringScroll || !key || key !== scrollStorageKey()) return
  try {
    sessionStorage.setItem(key, JSON.stringify({ left: window.scrollX, top: window.scrollY }))
  } catch { /* 存储不可用时保留浏览器默认行为 */ }
}

const restorePageScroll = () => {
  const key = scrollStorageKey()
  if (!key) return
  let position
  try { position = JSON.parse(sessionStorage.getItem(key) || 'null') } catch { position = null }
  if (!position || (!Number(position.top) && !Number(position.left))) return

  const targetTop = Math.max(0, Number(position.top) || 0)
  const targetLeft = Math.max(0, Number(position.left) || 0)
  let attempts = 0
  restoringScroll = true
  const restore = () => {
    if (key !== scrollStorageKey()) { restoringScroll = false; return }
    window.scrollTo(targetLeft, targetTop)
    attempts += 1
    const maximumTop = Math.max(0, document.documentElement.scrollHeight - window.innerHeight)
    if (attempts < 24 && maximumTop < targetTop) window.setTimeout(restore, 100)
    else window.setTimeout(() => { restoringScroll = false }, 150)
  }
  window.requestAnimationFrame(restore)
}

if ('scrollRestoration' in window.history) window.history.scrollRestoration = 'manual'
window.addEventListener('scroll', () => {
  window.clearTimeout(scrollSaveTimer)
  const key = scrollStorageKey()
  scrollSaveTimer = window.setTimeout(() => savePageScroll(key), 120)
}, { passive: true })
window.addEventListener('pagehide', () => savePageScroll())
window.addEventListener('beforeunload', () => savePageScroll())
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') savePageScroll()
})

const normalizeInput = (element) => {
  const normalized = normalizeMoneyInput(element.value)
  if (normalized === element.value) return
  element.value = normalized
  element.dispatchEvent(new Event('input', { bubbles: true }))
}

const app = createApp(App)
app.directive('money-input', {
  mounted(element) {
    normalizeInput(element)
    element.__moneyInputBlur = () => normalizeInput(element)
    element.addEventListener('blur', element.__moneyInputBlur)
  },
  updated(element) {
    if (document.activeElement !== element) normalizeInput(element)
  },
  unmounted(element) {
    element.removeEventListener('blur', element.__moneyInputBlur)
  },
})
app.use(router).mount('#app')
router.isReady().then(() => restorePageScroll())
