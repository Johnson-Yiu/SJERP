import { beforeEach } from 'vitest'
import { setAccessOperator } from '../src/accessControl.js'

// Existing component suites exercise business behavior as a local developer.
// RBAC-focused specs replace this operator with restricted permission matrices.
beforeEach(() => {
  setAccessOperator({
    name: '本地测试开发者',
    authenticated: true,
    development_superadmin: true,
    has_all_permissions: true,
    rbac_enforcement: false,
    can_manage_permissions: true,
    permissions: {},
  })
})
