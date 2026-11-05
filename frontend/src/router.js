import { createRouter, createWebHistory } from 'vue-router'
import { routes } from './workspaceRoutes'
export { routes } from './workspaceRoutes'
import { navigationAccess } from './navigationAccess'

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(navigationAccess)

export default router
