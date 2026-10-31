import { expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SharedReportTemplates from '../src/components/reports/SharedReportTemplates.vue'

const template = {
  id: 7, name: '国家客户销售', description: '团队共用销售查询', published: true,
  can_use: true, can_manage: true, updated_at: '2026-10-23T09:00:00Z', creator_name: '经理', config_version: 2,
  config: { source: 'sales', group_by: 'country', group_by_2: 'customer', filters: {} },
}

it('exposes shared-template actions without native confirm dialogs', async () => {
  const wrapper = mount(SharedReportTemplates, {
    props: { templates: [template], canCreate: true, canManage: true, canDelete: true, currentReady: true },
  })
  await wrapper.get('button').trigger('click')
  expect(wrapper.emitted('refresh')).toBeTruthy()
  await wrapper.get('.template-actions button').trigger('click')
  expect(wrapper.emitted('use')[0][0]).toEqual(template)
  await wrapper.findAll('.template-actions button')[3].trigger('click')
  expect(wrapper.text()).toContain('确认删除')
  await wrapper.find('.template-confirm .danger').trigger('click')
  expect(wrapper.emitted('delete')[0][0]).toEqual(template)
})

it('edits a template name through the local editor payload', async () => {
  const wrapper = mount(SharedReportTemplates, {
    props: { templates: [template], canCreate: true, canManage: true, currentReady: true, editor: { mode: 'edit', id: 7, name: template.name, description: template.description, version: 2 } },
  })
  await wrapper.find('input').setValue('新的团队模板')
  await wrapper.find('form').trigger('submit')
  expect(wrapper.emitted('save')[0][0]).toMatchObject({ name: '新的团队模板', description: template.description })
})
