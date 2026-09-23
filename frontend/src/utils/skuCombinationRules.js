export function matchesCombinationRules(values, rules, definitions) {
  const get = key => {
    const attribute = definitions.find(d => d.key === key)
    if (!attribute) return ''
    const suffix = key.split(':').at(-1).toLowerCase()
    const aliases = [suffix, suffix.split('/')[0], attribute.name?.toLowerCase()]
    const matches = Object.entries(values).filter(([k]) => aliases.includes(k.split(':').at(-1).toLowerCase()))
    return normalize(values[key] ?? (matches.length === 1 ? matches[0][1] : ''), attribute.unit)
  }
  const normalize = (value, unit = '') => {
    let text = String(value ?? '').trim().toLowerCase()
    unit = String(unit || '').trim().toLowerCase()
    if (text && unit && !text.endsWith(unit)) text += unit
    return text.replace(/\s+/g, ' ')
  }
  return rules.every(rule => {
    if (!definitions.some(d => d.key === rule.target) || (rule.when && !definitions.some(d => d.key === rule.when))) return false
    const normalized = (key, options) => (options || []).map(v => normalize(v, definitions.find(d => d.key === key)?.unit))
    if (rule.when && !normalized(rule.when, rule.when_values).includes(get(rule.when))) return true
    const included = normalized(rule.target, rule.values).includes(get(rule.target))
    return rule.op === 'neq' ? !included : included
  })
}
