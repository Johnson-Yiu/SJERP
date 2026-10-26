import { describe, expect, it } from 'vitest'
import { formatPiAmountWords } from '../src/utils/piAmountWords.js'
import { roundPiMoney } from '../src/utils/piMoney.js'

describe('PI amount in words', () => {
  it('rounds each displayed line before subtotal reconciliation', () => {
    expect(roundPiMoney(1.005)).toBe(1.01)
    expect(roundPiMoney(1.005) + roundPiMoney(1.005)).toBe(2.02)
    expect(roundPiMoney(1.005 + 1.005)).toBe(2.01)
  })

  it('renders the saved USD 246.00 total exactly', () => {
    expect(formatPiAmountWords(246, 'USD')).toBe('SAY TOTAL US DOLLARS TWO HUNDRED FORTY SIX ONLY')
  })

  it('renders cents for USD 246.50', () => {
    expect(formatPiAmountWords(246.5, 'USD')).toBe('SAY TOTAL US DOLLARS TWO HUNDRED FORTY SIX AND CENTS FIFTY ONLY')
  })

  it.each([
    ['EUR', 'EUROS'],
    ['GBP', 'POUNDS STERLING'],
    ['CNY', 'CHINA YUAN'],
    ['RMB', 'CHINA YUAN'],
  ])('uses the %s currency name', (code, label) => {
    expect(formatPiAmountWords(246, code)).toBe(`SAY TOTAL ${label} TWO HUNDRED FORTY SIX ONLY`)
  })

  it('renders zero totals and rejects invalid amount or currency data without placeholder text', () => {
    expect(formatPiAmountWords(0, 'USD')).toBe('SAY TOTAL US DOLLARS ZERO ONLY')
    for (const text of [
      formatPiAmountWords(undefined, 'USD'),
      formatPiAmountWords('NaN', 'USD'),
      formatPiAmountWords(10, undefined),
      formatPiAmountWords(10, 'null'),
    ]) {
      expect(text).toBe('')
      expect(text).not.toMatch(/undefined|null|NaN/i)
    }
  })
})
