<script setup>
import { computed, provide, reactive } from 'vue'
import { RouterView, routerKey, routeLocationKey, routerViewLocationKey } from 'vue-router'
import { workspaceKey, workspaceManagerKey } from '../composables/useWorkspaceNavigation'
const props = defineProps({ tab: Object, manager: Object })
const router = props.tab.router
provide(routerKey, router)
const route = reactive(Object.fromEntries(Object.keys(router.currentRoute.value).map(key => [key, computed(() => router.currentRoute.value[key])])))
provide(routeLocationKey, route)
provide(routerViewLocationKey, router.currentRoute)
provide(workspaceKey, props.tab)
provide(workspaceManagerKey, props.manager)
</script>
<template>
  <section :id="`workspace-panel-${tab.id}`" role="tabpanel" :aria-label="tab.title" v-show="tab.active" :inert="!tab.active" :aria-hidden="!tab.active" class="workspace-pane" :data-workspace="tab.id">
    <RouterView :key="tab.revision" />
  </section>
</template>
