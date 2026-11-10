import { accessState } from '../accessControl'

const root = 'sunjack:finance-attempt:v2:'
const oldAttemptKey = /^(finance-(receipt|plan-settle|purchase-payment|allocation|refund)-|sunjack:cash-(event:(pending-|request-identity)|confirm:)|sunjack:r1-fin-p2-b:cash-event-draft)/

function account() {
  const user = accessState.operator
  if (user?.authenticated && user.user_id != null) return `user:${user.user_id}`
  return user?.development_superadmin && !user.authenticated ? 'development' : null
}

class FinanceAttemptAccountError extends Error {}

export function financeAttemptError(error, fallback) {
  return error instanceof FinanceAttemptAccountError ? error.message : fallback
}

export function useFinanceAttempts() {
  let owner = account()
  const current = () => {
    if (!accessState.loaded || accessState.loading || accessState.error) return null
    const verified = account()
    if (!verified) return null
    owner ??= verified
    return verified === owner ? `${root}${owner}:` : null
  }
  return {
    isReady() { return Boolean(current()) },
    get(key) {
      const prefix = current()
      return prefix ? window.localStorage.getItem(prefix + key) : null
    },
    has(key) {
      try { return Boolean(this.get(key)) }
      catch { return false }
    },
    list(keyPrefix) {
      const prefix = current()
      return prefix ? Object.keys(window.localStorage)
        .filter(key => key.startsWith(prefix + keyPrefix))
        .map(key => key.slice(prefix.length)) : []
    },
    save(key, value) {
      const prefix = current()
      if (!prefix) throw new FinanceAttemptAccountError(
        accessState.error ? '账号权限核对失败，输入已保留。请重新核对账号后重试。'
          : owner && account() && owner !== account() ? '当前账号已切换，请返回原账号核对这笔操作。'
            : '正在核对账号权限，输入已保留。请稍后重试。',
      )
      const storage = window.localStorage
      const previous = storage.getItem(prefix + key)
      if (previous !== null && previous !== value) throw new Error('Another finance attempt is pending')
      storage.setItem(prefix + key, value)
    },
    remove(key, expected) {
      if (!owner || typeof expected !== 'string') return
      const storage = window.localStorage
      const storageKey = `${root}${owner}:${key}`
      if (storage.getItem(storageKey) === expected) storage.removeItem(storageKey)
    },
    hasLegacy() {
      try {
        return [...Object.keys(window.sessionStorage), ...Object.keys(window.localStorage)].some(key => oldAttemptKey.test(key))
      } catch { return false }
    },
  }
}
