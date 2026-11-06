let epoch = 0
const listeners = new Set()
export function sessionEpoch() { return epoch }
export function advanceSessionEpoch() { epoch += 1 }
export function onWorkspaceWrite(listener) { listeners.add(listener); return () => listeners.delete(listener) }
export function notifyWorkspaceWrite(source) { for (const listener of listeners) listener(source) }

const boundaryListeners = new Set()
export function onSessionBoundary(listener) { boundaryListeners.add(listener); return () => boundaryListeners.delete(listener) }
export function notifySessionBoundary() { for (const listener of boundaryListeners) listener() }

let accountScope = 'standalone'
export function setWorkspaceAccountScope(value) { accountScope = encodeURIComponent(value) }
export function workspaceAccountScope() { return accountScope }
