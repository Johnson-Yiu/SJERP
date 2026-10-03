<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { LayoutDashboard, Users, ContactRound, MessageSquareText, Package, Boxes, FileText, ShoppingCart, WalletCards, Upload, Tags, Menu, Warehouse, SlidersHorizontal, BadgeCheck, ShieldCheck, Truck, Barcode } from 'lucide-vue-next'
import { api } from './api'
import AppDialogHost from './components/AppDialogHost.vue'

const route = useRoute()
const menuOpen = ref(false)
const operator = reactive({ name: '加载中', role: '身份待确认', development_superadmin: false, has_all_permissions: false })
const nav = [
  { label: '经营概览', path: '/', icon: LayoutDashboard },
  { label: '报表中心', path: '/reports', icon: LayoutDashboard },
  { section: '客户' },
  { label: '客户管理', path: '/customers', icon: Users },
  { label: '联系人', path: '/contacts', icon: ContactRound },
  { label: '跟进记录', path: '/follow-ups', icon: MessageSquareText },
  { section: '销售业务' },
  { label: '报价管理', path: '/quotes', icon: FileText },
  { label: '订单管理', path: '/orders', icon: ShoppingCart },
  { section: '产品与供应链' },
  { label: '供应商管理', path: '/suppliers', icon: Truck },
  { label: '采购管理', path: '/purchase-orders', icon: ShoppingCart },
  { label: '产品管理', path: '/products', icon: Package },
  { label: 'HS 编码维护', path: '/hs-codes', icon: Barcode, requiresAdmin: true },
  { label: 'SKU 管理', path: '/skus', icon: Boxes },
  { label: '包装管理', path: '/sku-packaging', icon: Package },
  { label: '交易单位', path: '/sku-trade-units', icon: Boxes },
  { label: '库存流水', path: '/inventory-movements', icon: Warehouse },
  { label: '产品参数', path: '/product-parameters', icon: SlidersHorizontal },
  { label: '产品证书', path: '/product-certificates', icon: BadgeCheck },
  { label: '产品分类', path: '/categories', icon: Tags },
  { section: '财务与工具' },
  { label: '财务概览', path: '/finance', icon: WalletCards },
  { label: '应收计划', path: '/receivables', icon: WalletCards },
  { label: '应付计划', path: '/payables', icon: WalletCards },
  { label: '财务流水', path: '/transactions', icon: WalletCards },
  { label: '数据导入', path: '/import', icon: Upload },
  { section: '组织与系统' },
  { label: '组织与权限', path: '/organization', icon: ShieldCheck },
]
nav.splice(nav.findIndex(item => item.path === '/inventory-movements'), 0, { label: '库存', path: '/inventory', icon: Warehouse })
const currentDate = computed(() => new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'short' }).format(new Date()))
const operatorInitial = computed(() => operator.name && operator.name !== '加载中' ? operator.name.trim().slice(0, 1).toUpperCase() : '—')
const isAdmin = computed(() => operator.can_manage_hs_codes === true)
const visibleNav = computed(() => nav.filter(item => !item.requiresAdmin || isAdmin.value))
onMounted(async () => {
  try { Object.assign(operator, (await api.get('/session/current-operator/')).data) } catch { /* 保留默认展示 */ }
})
</script>

<template>
  <div class="app-shell">
    <div v-if="menuOpen" class="scrim" @click="menuOpen = false" />
    <aside class="sidebar" :class="{ open: menuOpen }">
      <div class="brand">
        <div class="brand-mark">S</div>
        <div><strong>森爵业务中台</strong><span>CRM · ERP</span></div>
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
        <div><strong>{{ operator.development_superadmin ? '开发身份' : '当前账号' }}：{{ operator.name }}</strong><small>{{ operator.role }} · {{ operator.has_all_permissions ? '全部功能与数据权限' : '按账号授权' }}</small></div>
      </div>
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
      <section class="content"><RouterView :key="route.fullPath" /></section>
    </main>
    <AppDialogHost />
  </div>
</template>
