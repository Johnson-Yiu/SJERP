// @vitest-environment jsdom
import { expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SegmentedDateInput from '../src/components/SegmentedDateInput.vue'

it('blocks stale valid date submission while preserving invalid visible input', async () => {
  const wrapper = mount(SegmentedDateInput, { props: { modelValue: '2026-02-20' } })
  await wrapper.get('[aria-label="日期"]').setValue('30')
  expect(wrapper.get('[role="alert"]').text()).toContain('有效且完整')
  expect(wrapper.get('[aria-label="年份"]').element.checkValidity()).toBe(false)
  expect(wrapper.get('[aria-label="日期"]').element.value).toBe('30')
  expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  await wrapper.get('[aria-label="日期"]').setValue('21')
  expect(wrapper.get('[aria-label="年份"]').element.checkValidity()).toBe(true)
  expect(wrapper.emitted('update:modelValue').at(-1)).toEqual(['2026-02-21'])
  wrapper.unmount()
})

it('allows an entirely blank optional date but rejects partial dates', async () => {
  const wrapper = mount(SegmentedDateInput)
  expect(wrapper.get('[aria-label="年份"]').element.checkValidity()).toBe(true)
  await wrapper.get('[aria-label="年份"]').setValue('2026')
  expect(wrapper.get('[aria-label="年份"]').element.checkValidity()).toBe(false)
  await wrapper.get('[aria-label="年份"]').setValue('')
  expect(wrapper.get('[aria-label="年份"]').element.checkValidity()).toBe(true)
  wrapper.unmount()
})
