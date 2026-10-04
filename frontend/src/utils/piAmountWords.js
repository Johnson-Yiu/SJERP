const currencyNames = Object.freeze({
  USD: 'US DOLLARS',
  EUR: 'EUROS',
  GBP: 'POUNDS STERLING',
  CNY: 'CHINA YUAN',
  RMB: 'CHINA YUAN',
})

const ones = Object.freeze([
  '', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE',
  'TEN', 'ELEVEN', 'TWELVE', 'THIRTEEN', 'FOURTEEN', 'FIFTEEN', 'SIXTEEN',
  'SEVENTEEN', 'EIGHTEEN', 'NINETEEN',
])
const tens = Object.freeze(['', '', 'TWENTY', 'THIRTY', 'FORTY', 'FIFTY', 'SIXTY', 'SEVENTY', 'EIGHTY', 'NINETY'])

function belowThousand(value) {
  const words = []
  if (value >= 100) {
    words.push(ones[Math.floor(value / 100)], 'HUNDRED')
    value %= 100
  }
  if (value >= 20) {
    words.push(tens[Math.floor(value / 10)])
    if (value % 10) words.push(ones[value % 10])
  } else if (value) words.push(ones[value])
  return words
}

function wholeNumberWords(value) {
  if (value === 0) return 'ZERO'
  const words = []
  for (const [divisor, label] of [[1_000_000_000, 'BILLION'], [1_000_000, 'MILLION'], [1_000, 'THOUSAND']]) {
    if (value >= divisor) {
      words.push(...belowThousand(Math.floor(value / divisor)), label)
      value %= divisor
    }
  }
  words.push(...belowThousand(value))
  return words.join(' ')
}

export function formatPiAmountWords(totalAmount, currency) {
  if (totalAmount === null || totalAmount === undefined || String(totalAmount).trim() === '') return ''
  const amount = Number(totalAmount)
  if (!Number.isFinite(amount) || amount < 0) return ''

  const currencyCode = typeof currency === 'string' ? currency.trim().toUpperCase() : ''
  if (!currencyCode || ['UNDEFINED', 'NULL', 'NAN'].includes(currencyCode)) return ''

  const totalCents = Math.round((amount + Number.EPSILON * Math.abs(amount)) * 100)
  if (!Number.isSafeInteger(totalCents)) return ''

  const whole = Math.floor(totalCents / 100)
  const cents = totalCents % 100
  const currencyName = currencyNames[currencyCode] || currencyCode
  const amountWords = `SAY TOTAL ${currencyName} ${wholeNumberWords(whole)}`
  return `${amountWords}${cents ? ` AND CENTS ${wholeNumberWords(cents)}` : ''} ONLY`
}
