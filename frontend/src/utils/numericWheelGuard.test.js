import { afterEach, describe, expect, it } from 'vitest'
import { installNumericWheelGuard } from './numericWheelGuard'

let removeGuard

afterEach(() => {
  removeGuard?.()
  removeGuard = undefined
  document.body.innerHTML = ''
})

function wheel(target, deltaY = 120) {
  const event = new WheelEvent('wheel', { bubbles: true, cancelable: true, deltaY })
  target.dispatchEvent(event)
  return event
}

describe('global numeric wheel guard', () => {
  it('cancels native wheel defaults and custom wheel handlers without changing the control', () => {
    document.body.innerHTML = '<input id="number" type="number" value="-12.5" step="0.1"><div id="custom" role="spinbutton">4</div>'
    removeGuard = installNumericWheelGuard()
    const number = document.querySelector('#number')
    const custom = document.querySelector('#custom')
    let inputEvents = 0
    let changeEvents = 0
    let customSteps = 0
    number.addEventListener('input', () => { inputEvents += 1 })
    number.addEventListener('change', () => { changeEvents += 1 })
    custom.addEventListener('wheel', () => { customSteps += 1 })

    const numberWheel = wheel(number)
    const customWheel = wheel(custom)

    expect(numberWheel.defaultPrevented).toBe(true)
    expect(customWheel.defaultPrevented).toBe(true)
    expect(number.value).toBe('-12.5')
    expect(custom.textContent).toBe('4')
    expect(customSteps).toBe(0)
    expect(inputEvents).toBe(0)
    expect(changeEvents).toBe(0)
  })

  it('guards the focused numeric control even when the pointer is elsewhere', () => {
    document.body.innerHTML = '<input id="number" type="number" value="0.25" step="0.01"><div id="pointer"></div>'
    removeGuard = installNumericWheelGuard()
    const number = document.querySelector('#number')
    const pointer = document.querySelector('#pointer')
    number.focus()

    const event = wheel(pointer, -120)

    expect(event.defaultPrevented).toBe(true)
    expect(document.activeElement).toBe(number)
    expect(number.value).toBe('0.25')
  })

  it('leaves text inputs and textareas on the browser scroll path', () => {
    document.body.innerHTML = '<input id="text" type="text" value="plain"><textarea id="notes">notes</textarea>'
    removeGuard = installNumericWheelGuard()

    const textEvent = wheel(document.querySelector('#text'))
    const textareaEvent = wheel(document.querySelector('#notes'))

    expect(textEvent.defaultPrevented).toBe(false)
    expect(textareaEvent.defaultPrevented).toBe(false)
  })

  it('uses one delegated listener and removes it cleanly', () => {
    document.body.innerHTML = '<div id="rows"></div>'
    const firstRemove = installNumericWheelGuard()
    const secondRemove = installNumericWheelGuard()
    expect(secondRemove).toBe(firstRemove)

    const row = document.createElement('input')
    row.type = 'number'
    row.value = '3'
    document.querySelector('#rows').append(row)
    expect(wheel(row).defaultPrevented).toBe(true)

    firstRemove()
    expect(wheel(row).defaultPrevented).toBe(false)
    removeGuard = undefined
  })
})
