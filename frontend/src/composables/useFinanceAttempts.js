import { accessState } from '../accessControl'

const root = 'sunjack:finance-attempt:v2:'
const oldAttemptKey = /^(finance-(receipt|plan-settle|purchase-payment|allocation|refund)-|sunjack:cash-(event:(pending-|request-identity)|confirm:)|sunjack:r1-fin-p2-b:cash-event-draft)/

function account() {
  const user = accessState.operator
  if (!accessState.loaded || accessState.loading || accessState.error) return null
  if (user?.authenticated && user.user_id != null) return `user:${user.user_id}`
  return user?.development_superadmin && !user.authenticated ? 'development' : null
}

export function useFinanceAttempts() {
  const owner = account()
  const prefix = owner && `${root}${owner}:`
  const current = () => prefix && account() === owner
  return {
    get(key) { return current() ? window.localStorage.getItem(prefix + key) : null },
    has(key) {
      try { return Boolean(current() && window.localStorage.getItem(prefix + key)) }
      catch { return false }
    },
    list(keyPrefix) {
      return current() ? Object.keys(window.localStorage)
        .filter(key => key.startsWith(prefix + keyPrefix))
        .map(key => key.slice(prefix.length)) : []
    },
    save(key, value) {
      if (!current()) throw new Error('Finance account unavailable or changed')
      const storage = window.localStorage
      const previous = storage.getItem(prefix + key)
      if (previous !== null && previous !== value) throw new Error('Another finance attempt is pending')
      storage.setItem(prefix + key, value)
    },
    remove(key) { if (prefix) window.localStorage.removeItem(prefix + key) },
    hasLegacy() {
      try {
        return [...Object.keys(window.sessionStorage), ...Object.keys(window.localStorage)].some(key => oldAttemptKey.test(key))
      } catch { return false }
    },
  }
}
