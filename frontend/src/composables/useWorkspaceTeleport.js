import { computed, inject } from 'vue'
import { workspaceKey } from './useWorkspaceNavigation'

// Move inactive overlays back into the hidden, inert workspace pane.
// Keep components mounted so switching tabs preserves forms and requests.
export function useWorkspaceTeleportDisabled() {
  const workspace = inject(workspaceKey, null)
  return computed(() => Boolean(workspace && !workspace.active))
}
