import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles.css'
import { normalizeMoneyInput } from './utils/money'

const scrollStoragePrefix = 'senju:page-scroll:'
const scrollStorageKey = path => `${scrollStoragePrefix}${path}`
let scrollSaveTimer = null
let restoringScroll = false

const savePageScroll = (path = router.currentRoute.value.fullPath) => {
  if (restoringScroll || !path) return
  try {
    sessionStorage.setItem(scrollStorageKey(path), JSON.stringify({ left: window.scrollX, top: window.scrollY }))
  } catch { /* 存储不可用时保留浏览器默认行为 */ }
}

const restorePageScroll = (path = router.currentRoute.value.fullPath) => {
  let position
  try { position = JSON.parse(sessionStorage.getItem(scrollStorageKey(path)) || 'null') } catch { position = null }
  if (!position || (!Number(position.top) && !Number(position.left))) return

  const targetTop = Math.max(0, Number(position.top) || 0)
  const targetLeft = Math.max(0, Number(position.left) || 0)
  let attempts = 0
  restoringScroll = true
  const restore = () => {
    window.scrollTo(targetLeft, targetTop)
    attempts += 1
    const maximumTop = Math.max(0, document.documentElement.scrollHeight - window.innerHeight)
    if (attempts < 24 && maximumTop < targetTop) window.setTimeout(restore, 100)
    else window.setTimeout(() => { restoringScroll = false }, 150)
  }
  window.requestAnimationFrame(restore)
}

if ('scrollRestoration' in window.history) window.history.scrollRestoration = 'manual'
router.beforeEach((to, from) => {
  if (from?.fullPath) savePageScroll(from.fullPath)
})
window.addEventListener('scroll', () => {
  window.clearTimeout(scrollSaveTimer)
  scrollSaveTimer = window.setTimeout(() => savePageScroll(), 120)
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
