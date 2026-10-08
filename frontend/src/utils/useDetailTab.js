import { computed, inject, ref, watch } from 'vue'
import { routeLocationKey, routerKey } from 'vue-router'

// Keep workbench tabs in the current history entry so Back restores its context.
export function useDetailTab(path, allowed, fallback, id) {
  const route = inject(routeLocationKey, null)
  const router = inject(routerKey, null)
  const local = ref(fallback)
  const ownsRoute = () => route?.path === path && Boolean(route.query.detail) &&
    (!id || String(route.query.detail) === String(id()))
  const valid = value => typeof value === 'string' && allowed.includes(value) ? value : fallback
  const activeTab = computed({
    get: () => ownsRoute() ? valid(route.query.tab) : local.value,
    set: value => {
      local.value = valid(value)
      if (ownsRoute()) {
        void router.replace({ path: route.path, query: { ...route.query, tab: local.value }, hash: route.hash })
      }
    },
  })
  if (route && router) watch(() => [route.path, route.query.detail, route.query.tab, id?.()], () => {
    if (ownsRoute() && route.query.tab !== undefined && route.query.tab !== valid(route.query.tab)) activeTab.value = valid(route.query.tab)
  }, { immediate: true })
  return activeTab
}
