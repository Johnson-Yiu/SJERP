export function categoryParts(path) {
  return String(path || '').split(/\s*\/\s*/).map(value => value.trim()).filter(Boolean)
}

export function categoryContains(parent, path) {
  const prefix = categoryParts(parent), parts = categoryParts(path)
  return prefix.every((value, index) => value === parts[index])
}

export function categoryTree(paths) {
  const roots = []
  for (const path of paths) {
    let siblings = roots
    const parts = categoryParts(path)
    parts.forEach((name, index) => {
      let node = siblings.find(item => item.name === name)
      if (!node) {
        node = { name, value: parts.slice(0, index + 1).join(' / '), children: [] }
        siblings.push(node)
      }
      siblings = node.children
    })
  }
  return roots
}
