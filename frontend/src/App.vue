<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { LayoutDashboard, Users, ContactRound, MessageSquareText, Package, Boxes, FileText, ShoppingCart, WalletCards, Upload, Tags, Menu, Bell, Search, Warehouse, SlidersHorizontal, BadgeCheck, ShieldCheck, Truck } from 'lucide-vue-next'
import { api } from './api'

const route = useRoute()
const menuOpen = ref(false)
const operator = reactive({ name: 'Johnson', role: '超级管理员' })
const nav = [
  { label: '经营概览', path: '/', icon: LayoutDashboard },
  { section: '客户' },
  { label: '客户管理', path: '/customers', icon: Users },
  { label: '联系人', path: '/contacts', icon: ContactRound },
  { label: '跟进记录', path: '/follow-ups', icon: MessageSquareText },
  { section: '业务' },
  { label: '报价管理', path: '/quotes', icon: FileText },
  { label: '订单管理', path: '/orders', icon: ShoppingCart },
  { label: '供应商管理', path: '/suppliers', icon: Truck },
  { label: '采购管理', path: '/purchase-orders', icon: ShoppingCart },
  { label: '产品管理', path: '/products', icon: Package },
  { label: 'SKU 管理', path: '/skus', icon: Boxes },
  { label: '库存流水', path: '/inventory-movements', icon: Warehouse },
  { label: '产品参数', path: '/product-parameters', icon: SlidersHorizontal },
  { label: '产品证书', path: '/product-certificates', icon: BadgeCheck },
  { label: '产品分类', path: '/categories', icon: Tags },
  { section: '财务与工具' },
  { label: '财务流水', path: '/transactions', icon: WalletCards },
  { label: '数据导入', path: '/import', icon: Upload },
  { section: '组织与系统' },
  { label: '组织与权限', path: '/organization', icon: ShieldCheck },
]
nav.splice(nav.findIndex(item => item.path === '/inventory-movements'), 0, { label: '库存', path: '/inventory', icon: Warehouse })
const currentDate = computed(() => new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'short' }).format(new Date()))
const operatorInitial = computed(() => operator.name?.slice(0, 1).toUpperCase() || 'J')
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
        <template v-for="(item, index) in nav" :key="index">
          <div v-if="item.section" class="nav-section">{{ item.section }}</div>
          <RouterLink v-else :to="item.path" class="nav-item" @click="menuOpen = false">
            <component :is="item.icon" :size="18" />
            <span>{{ item.label }}</span>
          </RouterLink>
        </template>
      </nav>
      <div class="sidebar-foot">
        <div class="team-avatars"><span>{{ operatorInitial }}</span></div>
        <div><strong>当前账号：{{ operator.name }}</strong><small>{{ operator.role }} · 全部数据权限</small></div>
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
          <div class="quick-search"><Search :size="17" /><span>搜索客户、订单...</span><kbd>⌘ K</kbd></div>
          <span class="date-pill">{{ currentDate }}</span>
          <button class="icon-btn"><Bell :size="19" /><i /></button>
          <div class="avatar">J</div>
        </div>
      </header>
      <section class="content"><RouterView :key="route.fullPath" /></section>
    </main>
  </div>
</template>
