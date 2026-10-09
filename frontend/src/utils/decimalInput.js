// Compact editable decimal text without numeric conversion or rounding.
export function compactDecimalInput(value) {
  if (value == null) return ''
  const text = String(value)
  if (!/^[+-]?\d+\.\d+$/.test(text)) return text
  return text.replace(/0+$/, '').replace(/\.$/, '')
}

// Keep terminating decimal prices exact when changing receipt packaging.
export function scaleDecimalInput(value, previousFactor, nextFactor) {
  const parse = value => {
    const text = String(value)
    if (!/^[+-]?\d+(?:\.\d+)?$/.test(text)) return null
    const [whole, fraction = ''] = text.split('.')
    return [BigInt(whole + fraction), 10n ** BigInt(fraction.length)]
  }
  const price = parse(value), previous = parse(previousFactor), next = parse(nextFactor)
  if (!price || !previous || !next || previous[0] === 0n) return compactDecimalInput(Number(value) / Number(previousFactor) * Number(nextFactor))
  let numerator = price[0] * next[0] * previous[1]
  let denominator = price[1] * next[1] * previous[0]
  if (denominator < 0n) { numerator = -numerator; denominator = -denominator }
  const negative = numerator < 0n
  numerator = negative ? -numerator : numerator
  const gcd = (a, b) => { while (b) [a, b] = [b, a % b]; return a }
  const divisor = gcd(numerator, denominator)
  numerator /= divisor; denominator /= divisor
  let rest = denominator
  while (rest % 2n === 0n) rest /= 2n
  while (rest % 5n === 0n) rest /= 5n
  // Repeating ratios have no finite exact decimal; retain JS numeric conversion.
  if (rest !== 1n) return compactDecimalInput(Number(value) / Number(previousFactor) * Number(nextFactor))
  const whole = numerator / denominator
  let remainder = numerator % denominator, fraction = ''
  while (remainder) { remainder *= 10n; fraction += remainder / denominator; remainder %= denominator }
  return `${negative && numerator ? '-' : ''}${whole}${fraction ? '.' + fraction : ''}`
}
