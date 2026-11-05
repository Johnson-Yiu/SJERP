import { inject } from 'vue'
export const workspaceKey = Symbol('business-workspace')
export const workspaceManagerKey = Symbol('workspace-manager')
// A no-op fallback keeps standalone page mounts and existing hosts compatible.
export function useWorkspaceNavigation() {
  const workspace = inject(workspaceKey, null)
  const manager = inject(workspaceManagerKey, null)
  return {
    workspace,
    openTask(location, options) { return manager?.open(location, options) },
    adoptObject(location) { return manager?.adopt(workspace, location) },
    confirmExit() { return manager?.confirmExit() ?? Promise.resolve(true) },
    newDraft(location) { return manager?.open(location, { fresh: true }) },
    storageKey(key) { return workspace ? `${key}:${manager.identity.value}:${workspace.id}` : key },
  }
}
