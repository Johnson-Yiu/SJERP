import { describe, expect, it } from 'vitest'
import { compactDecimalInput, scaleDecimalInput } from '../src/utils/decimalInput'

describe('editable decimal text', () => {
  it.each([
    ['7.200000','7.2'], ['34.0000','34'], ['34.1250','34.125'],
    ['0.000001','0.000001'], ['100','100'], ['', ''], [null,''], [undefined,''],
    ['34.1257','34.1257'], ['12345678901234567890.123456789000','12345678901234567890.123456789'],
    ['-0.0100','-0.01'], ['1e-7','1e-7'],
  ])('compacts %s without rounding to %s', (raw, result) => {
    expect(compactDecimalInput(raw)).toBe(result)
    if (raw != null && raw !== '') expect(Number(result)).toBe(Number(raw))
  })
  it('retains exact significant receipt digits across packaging changes and back', () => {
    expect(scaleDecimalInput('34.1257000','5.000000','10.000000')).toBe('68.2514')
    expect(scaleDecimalInput('68.2514','10','5')).toBe('34.1257')
    expect(scaleDecimalInput('0.000001','5','1')).toBe('0.0000002')
    expect(scaleDecimalInput('12345678901234567890.123456789','1','10')).toBe('123456789012345678901.23456789')
  })
})
