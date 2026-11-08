const installs = new WeakMap()
const NUMERIC_CONTROL = 'input[type="number" i], [role="spinbutton"]'
const SCROLLABLE_OVERFLOW = new Set(['auto', 'scroll', 'overlay'])

function isElement(value, view) {
  return value instanceof view.Element
}

function eventPath(event, view) {
  if (typeof event.composedPath === 'function') {
    const path = event.composedPath()
    if (path.length) return path
  }

  const path = []
  for (let node = event.target; node; node = node.parentNode) path.push(node)
  path.push(view, view.document)
  return path
}

function wheelAmount(event, axis, path, document, view) {
  const delta = axis === 'y' ? event.deltaY : event.deltaX
  if (!delta) return 0
  if (event.deltaMode === 0) return delta
  if (event.deltaMode === 2) return delta * Math.max(1, axis === 'y' ? view.innerHeight : view.innerWidth)

  const origin = path.find(node => isElement(node, view))
  const style = origin ? view.getComputedStyle(origin) : null
  const lineHeight = Number.parseFloat(style?.lineHeight)
  const fontSize = Number.parseFloat(style?.fontSize)
  return delta * (Number.isFinite(lineHeight) ? lineHeight : Number.isFinite(fontSize) ? fontSize * 1.2 : 19)
}

function canScroll(element, axis, amount) {
  const size = axis === 'y' ? element.scrollHeight - element.clientHeight : element.scrollWidth - element.clientWidth
  if (size <= 0) return false
  const position = axis === 'y' ? element.scrollTop : element.scrollLeft
  return amount > 0 ? position < size - 0.5 : position > 0.5
}

function hasScrollRange(element, axis) {
  return axis === 'y'
    ? element.scrollHeight > element.clientHeight
    : element.scrollWidth > element.clientWidth
}

function containsOverscroll(style, axis) {
  const value = axis === 'y'
    ? style.overscrollBehaviorY || style.overscrollBehavior
    : style.overscrollBehaviorX || style.overscrollBehavior
  return value === 'contain' || value === 'none'
}

function findScrollDestination(path, axis, amount, document, view) {
  if (!amount) return null
  const root = document.scrollingElement || document.documentElement

  for (const candidate of path) {
    if (!isElement(candidate, view) || !(candidate instanceof view.HTMLElement) || candidate === root || candidate === document.body) continue

    const style = view.getComputedStyle(candidate)
    const overflow = axis === 'y' ? style.overflowY : style.overflowX
    if (!SCROLLABLE_OVERFLOW.has(overflow)) continue
    if (canScroll(candidate, axis, amount)) return candidate
    if (hasScrollRange(candidate, axis) && containsOverscroll(style, axis)) return null
  }

  return root && canScroll(root, axis, amount) ? root : null
}

function applyWheelScroll(event, path, document, view) {
  const dx = wheelAmount(event, 'x', path, document, view)
  const dy = wheelAmount(event, 'y', path, document, view)
  const xTarget = findScrollDestination(path, 'x', dx, document, view)
  const yTarget = findScrollDestination(path, 'y', dy, document, view)

  if (xTarget) xTarget.scrollLeft += dx
  if (yTarget) yTarget.scrollTop += dy
}

/**
 * Stop wheel-driven number changes while forwarding the same scroll distance
 * to the nearest scrollable ancestor. The delegated listener also covers
 * routed views, dynamic rows, dialogs, drawers and workspace tabs.
 */
export function installNumericWheelGuard(document = globalThis.document) {
  const view = document?.defaultView
  if (!view) return () => {}

  const previous = installs.get(document)
  if (previous) return previous

  const onWheel = event => {
    const path = eventPath(event, view)
    const targetIsNumeric = path.some(node => isElement(node, view) && node.matches(NUMERIC_CONTROL))
    const activeIsNumeric = isElement(document.activeElement, view) && document.activeElement.matches(NUMERIC_CONTROL)
    if (!targetIsNumeric && !activeIsNumeric) return

    if (event.cancelable) {
      event.preventDefault()
      if (event.defaultPrevented) applyWheelScroll(event, path, document, view)
    }
    event.stopImmediatePropagation()
  }

  view.addEventListener('wheel', onWheel, { capture: true, passive: false })
  let installed = true
  const remove = () => {
    if (!installed) return
    installed = false
    view.removeEventListener('wheel', onWheel, true)
    installs.delete(document)
  }
  installs.set(document, remove)
  return remove
}
