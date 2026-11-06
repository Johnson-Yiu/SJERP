<script setup>
import { computed, onMounted, onBeforeUnmount, ref, provide, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LayoutDashboard, Users, ContactRound, MessageSquareText, Package, Boxes, FileText, ShoppingCart, WalletCards, Upload, Tags, Menu, Warehouse, SlidersHorizontal, BadgeCheck, ShieldCheck, Truck, Barcode, History } from 'lucide-vue-next'
import AppDialogHost from './components/AppDialogHost.vue'
import { withoutModalActionQuery } from './utils/routePageState'
import { onSessionBoundary } from './workspaceSession'
import WorkspaceTabs from './components/WorkspaceTabs.vue'
import WorkspacePane from './components/WorkspacePane.vue'
import { createWorkspaceManager } from './workspaceManager'
import { workspaceManagerKey } from './composables/useWorkspaceNavigation'
import { accessState, can, canAccessHistoricalOrders, canAccessOrganization, loadAccessControl, setAccessOperator } from './accessControl'
import { api } from './api'

const route = useRoute()
const rootRouter = useRouter()
const manager = createWorkspaceManager(rootRouter)
provide(workspaceManagerKey, manager)
watch(() => accessState.operator, async value => {
  const identity = value ? String(value.user_id ?? value.id ?? value.employee_profile_id ?? (value.development_superadmin && !value.authenticated ? 'development' : 'unidentified-session')) : 'anonymous'
  manager.reset(identity)
  if (value?.authenticated || value?.development_superadmin) {
    await rootRouter.isReady()
    const current = rootRouter.currentRoute.value
    if (current.name !== 'login' && accessState.operator === value && !manager.tabs.length && !manager.isOpening()) await manager.open(current.fullPath)
  }
}, { immediate: true, flush: 'sync' })
const removeBoundary = onSessionBoundary(() => {
  const current = rootRouter.currentRoute.value
  const next = rootRouter.resolve({ path: current.path, query: withoutModalActionQuery(current.query), hash: current.hash }).fullPath
  setAccessOperator(null)
  manager.reset('expired')
  menuOpen.value = false
  void rootRouter.replace({ name: 'login', query: { reason: 'expired', next }, state: { __workspace: null } })
})
onBeforeUnmount(() => { removeBoundary(); manager.destroy() })
const menuOpen = ref(false)
const signOutError = ref('')
const operator = computed(() => accessState.operator || { name: accessState.error ? '权限状态不可用' : '加载中', role: '身份待确认', development_superadmin: false, has_all_permissions: false })
const nav = [
  { section: '经营' },
  { label: '经营概览', path: '/', module: 'dashboard', icon: LayoutDashboard },
  { label: '报表中心', path: '/reports', module: 'reports', icon: LayoutDashboard },
  { label: '历史订单分析', path: '/historical-orders', module: 'reports', icon: History },
  { section: '客户' },
  { label: '客户管理', path: '/customers', module: 'customers', icon: Users },
  { label: '联系人', path: '/contacts', module: 'contacts', icon: ContactRound },
  { label: '跟进记录', path: '/follow-ups', module: 'followups', icon: MessageSquareText },
  { section: '销售' },
  { label: '报价管理', path: '/quotes', module: 'quotes', icon: FileText },
  { label: '订单管理', path: '/orders', module: 'orders', icon: ShoppingCart },
  { section: '采购与库存' },
  { label: '供应商管理', path: '/suppliers', module: 'suppliers', icon: Truck },
  { label: '采购管理', path: '/purchase-orders', module: 'purchases', icon: ShoppingCart },
  { label: '库存', path: '/inventory', module: 'inventory', icon: Warehouse },
  { label: '库存流水', path: '/inventory-movements', module: 'inventory', icon: Warehouse },
  { section: '产品资料' },
  { label: '产品管理', path: '/products', module: 'products', icon: Package },
  { label: 'SKU 管理', path: '/skus', module: 'skus', icon: Boxes },
  { label: '产品分类', path: '/categories', module: 'categories', icon: Tags },
  { label: '产品参数', path: '/product-parameters', module: 'parameters', icon: SlidersHorizontal },
  { label: '包装管理', path: '/sku-packaging', module: 'packaging', icon: Package },
  { label: '交易单位', path: '/sku-trade-units', module: 'trade_units', icon: Boxes },
  { label: '产品证书', path: '/product-certificates', module: 'certificates', icon: BadgeCheck },
  { label: 'HS 编码维护', path: '/hs-codes', module: 'hs_codes', icon: Barcode },
  { section: '财务与工具' },
  { label: '财务概览', path: '/finance', module: 'finance', icon: WalletCards },
  { label: '应收计划', path: '/receivables', module: 'finance', icon: WalletCards },
  { label: '应付计划', path: '/payables', module: 'finance', icon: WalletCards },
  { label: '财务流水', path: '/transactions', module: 'transactions', icon: WalletCards },
  { label: '人民币资金', path: '/rmb-cash-events', module: 'transactions', icon: WalletCards },
  { label: '账户资金', path: '/finance-ledger', module: 'finance', icon: WalletCards },
  { label: '数据导入', path: '/import', module: 'imports', icon: Upload },
  { label: '历史资料预检', path: '/history-preflight', module: 'imports', icon: History },
  { label: '历史资料承接', path: '/history-takeover', module: 'imports', icon: History },
  { section: '组织与系统' },
  { label: '组织与权限', path: '/organization', module: 'organization', icon: ShieldCheck },
]
const currentDate = computed(() => new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'short' }).format(new Date()))
const operatorInitial = computed(() => operator.value.name && operator.value.name !== '加载中' ? operator.value.name.trim().slice(0, 1).toUpperCase() : '—')
const visibleNav = computed(() => {
  const result = []
  let title = '', entries = []
  const flush = () => { if (entries.length) result.push({ section: title }, ...entries); entries = [] }
  for (const item of nav) {
    if (item.section) { flush(); title = item.section }
    else if (item.path === '/organization' ? canAccessOrganization() : item.path === '/historical-orders' ? canAccessHistoricalOrders() : can(item.module, 'view')) entries.push(item)
  }
  flush()
  return result
})
onMounted(() => { loadAccessControl().catch(() => {}) })
const signingOut = ref(false)
async function signOut() {
  if (signingOut.value) return
  signingOut.value = true
  signOutError.value = ''
  try {
    if (!await manager.confirmExit() || accessState.operator?.authenticated !== true) return
    await api.get('/session/csrf/')
    await api.post('/session/logout/')
    setAccessOperator(null)
    menuOpen.value = false
    await rootRouter.replace({ name: 'login', state: { __workspace: null } })
  } catch { signOutError.value = '退出未完成，请检查网络后重试。' }
  finally { signingOut.value = false }
}
</script>

<template>
  <RouterView v-if="route.name === 'login'" />
  <div v-else class="app-shell">
    <div v-if="menuOpen" class="scrim" @click="menuOpen = false" />
    <aside class="sidebar" :class="{ open: menuOpen }">
      <div class="brand">
        <div class="brand-mark">S</div>
        <div><strong>森爵照明管理系统</strong><span>客户 · 销售 · 产品</span></div>
      </div>
      <nav>
        <template v-for="(item, index) in visibleNav" :key="index">
          <div v-if="item.section" class="nav-section">{{ item.section }}</div>
          <RouterLink v-else :to="item.path" class="nav-item" @click="menuOpen = false">
            <component :is="item.icon" :size="18" />
            <span>{{ item.label }}</span>
          </RouterLink>
        </template>
      </nav>
      <div class="sidebar-foot">
        <div class="team-avatars"><span>{{ operatorInitial }}</span></div>
        <div class="sidebar-identity"><strong :title="operator.name">{{ operator.development_superadmin ? '开发身份' : '当前账号' }}：{{ operator.name }}</strong><small>{{ operator.role }} · {{ operator.has_all_permissions ? '全部功能与数据权限' : '按账号授权' }}</small></div>
        <button v-if="operator.authenticated && !operator.development_superadmin" type="button" :disabled="signingOut" @click="signOut">退出登录</button>
      </div>
      <div v-if="accessState.error" class="access-state-error" role="alert">权限状态加载失败：{{ accessState.error }}</div>
      <div v-if="signOutError" class="access-state-error" role="alert">{{ signOutError }}</div>
    </aside>

    <main class="main">
      <header class="topbar">
        <button class="icon-btn mobile-menu" @click="menuOpen = true"><Menu :size="21" /></button>
        <div class="page-identity">
          <small>{{ route.meta.eyebrow }}</small>
          <h1>{{ route.meta.title }}</h1>
        </div>
        <div class="top-actions">
          <span class="date-pill">{{ currentDate }}</span>
          <div class="avatar" :title="operator.name">{{ operatorInitial }}</div>
        </div>
      </header>
      <WorkspaceTabs :manager="manager" />
      <section class="content"><WorkspacePane v-for="tab in manager.tabs" :key="tab.id" :tab="tab" :manager="manager" /></section>
    </main>
    <AppDialogHost />
  </div>
</template>
