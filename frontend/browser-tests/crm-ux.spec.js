import { expect, test } from '@playwright/test'

const customers = [
  { id: 1, name: '长名称客户 · 照明采购与工程项目部', code: 'C-0001', next_follow_up: '2026-10-20' },
  { id: 2, name: '另一家客户', code: 'C-0002', next_follow_up: null },
]
const contacts = Array.from({ length: 60 }, (_, index) => ({
  id: index + 1,
  customer: index < 45 ? 1 : 2,
  customer_name: index < 45 ? customers[0].name : customers[1].name,
  name: index % 2 ? `联系人 ${index + 1}` : `Lin Yu ${index + 1}`,
  title: '采购负责人与国际项目业务协调'.repeat(2),
  email: `contact${index + 1}@example.test`,
  phone: `+86 1380000${String(index + 1).padStart(4, '0')}`,
  whatsapp: `+86 1390000${String(index + 1).padStart(4, '0')}`,
  is_primary: index === 0 || index === 45,
  notes: '隔离验收联系人',
}))
const followUps = Array.from({ length: 32 }, (_, index) => ({
  id: index + 1,
  customer: index < 20 ? 1 : 2,
  customer_name: index < 20 ? customers[0].name : customers[1].name,
  contact: index < 20 ? 1 : 25,
  contact_name: index < 20 ? contacts[0].name : contacts[24].name,
  followed_at: `2026-10-${String(14 - index % 12).padStart(2, '0')}T09:30:00+08:00`,
  type: index % 2 ? 'phone' : 'email',
  type_display: index % 2 ? '电话' : '邮件',
  subject: `产品资料沟通 ${index + 1}`,
  content: `<p>${'长段沟通记录用于列表换行和详情阅读。'.repeat(10)}</p>`,
  result: `<p>客户回复：规格和报价需要复核。${index + 1}</p>`,
  next_action: '发送更新后的报价并确认交期',
  next_follow_up: index < 20 ? '2026-10-20' : '2026-11-01',
  next_follow_up_mode: 'set',
  next_follow_up_mode_display: '设置新的跟进日期',
  owner: '开发验收',
  attachments: [{ id: index + 1, name: `验收附件-${index + 1}.txt`, size: 96, url: '/media/f4.txt', content_type: 'text/plain' }],
}))

function detail(entity, row) {
  if (entity === 'contacts') return {
    entity, title: row.name, subtitle: `${row.title} · ${row.customer_name}`, badge: row.is_primary ? '主联系人' : '联系人',
    info: [['关联企业', row.customer_name], ['邮箱', row.email], ['电话', row.phone], ['WhatsApp', row.whatsapp], ['备注', row.notes]], metrics: [['跟进次数', 1, 'number']],
    sections: [{ key: 'company', title: '所属客户', entity: 'customers', columns: [['name', '客户']], rows: [customers.find(item => item.id === row.customer)] }, { key: 'followups', title: '跟进记录', entity: 'follow-ups', columns: [['subject', '主题']], rows: followUps.filter(item => item.contact === row.id) }],
  }
  return {
    entity, title: row.subject, subtitle: `${row.customer_name} · ${row.followed_at}`, badge: row.type_display,
    info: [['跟进人', row.owner], ['跟进记录 / 解决方案', row.content, 'richtext'], ['客户回复 / 客户疑问', row.result, 'richtext'], ['下一步', row.next_action], ['下次跟进安排', row.next_follow_up_mode_display], ['下次跟进', row.next_follow_up]],
    attachments: row.attachments, metrics: [], sections: [
      { key: 'customer', title: '客户', entity: 'customers', columns: [['name', '客户']], rows: [customers.find(item => item.id === row.customer)] },
      { key: 'contact', title: '联系人', entity: 'contacts', columns: [['name', '姓名'], ['title', '职位']], rows: [contacts.find(item => item.id === row.contact)] },
    ],
  }
}

async function mockApi(page) {
  const state = { contacts: structuredClone(contacts), followUps: structuredClone(followUps), posts: [], puts: [], deletes: [], uploads: [], attachmentDeletes: [] }
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    if (path === '/api/session/current-operator/') return route.fulfill({ json: { authenticated: true, development_superadmin: true, has_all_permissions: true, name: '开发验收' } })
    if (path === '/api/customers/') return route.fulfill({ json: customers })
    if (path === '/api/follow-ups/methods/') return route.fulfill({ json: [{ value: 'phone', label: '电话' }, { value: 'email', label: '邮件' }] })
    if (path.startsWith('/api/context/contacts/')) {
      const row = state.contacts.find(item => item.id === Number(path.split('/')[4]))
      return route.fulfill({ json: detail('contacts', row) })
    }
    if (path.startsWith('/api/context/follow-ups/')) {
      const row = state.followUps.find(item => item.id === Number(path.split('/')[4]))
      return route.fulfill({ json: detail('follow-ups', row) })
    }
    if (path === '/api/operation-logs/') return route.fulfill({ json: [] })
    if (path === '/api/contacts/' && method === 'GET') return route.fulfill({ json: state.contacts.filter(row => (!url.searchParams.get('customer') || String(row.customer) === url.searchParams.get('customer')) && (!url.searchParams.get('search') || `${row.name} ${row.title} ${row.customer_name} ${row.email} ${row.phone} ${row.whatsapp}`.toLowerCase().includes(url.searchParams.get('search').toLowerCase()))) })
    if (path === '/api/follow-ups/' && method === 'GET') return route.fulfill({ json: state.followUps.filter(row => (!url.searchParams.get('customer') || String(row.customer) === url.searchParams.get('customer')) && (url.searchParams.get('due') !== 'true' || row.next_follow_up <= '2026-10-20') && (!url.searchParams.get('search') || `${row.subject} ${row.content} ${row.customer_name} ${row.owner}`.toLowerCase().includes(url.searchParams.get('search').toLowerCase()))) })
    const contactMatch = path.match(/^\/api\/contacts\/(\d+)\/$/)
    const followUpMatch = path.match(/^\/api\/follow-ups\/(\d+)\/$/)
    if (path === '/api/contacts/' && method === 'POST') {
      const data = route.request().postDataJSON(); state.posts.push(data)
      const row = { ...data, id: 100, customer_name: customers.find(item => item.id === Number(data.customer))?.name }
      state.contacts.unshift(row)
      return route.fulfill({ json: row })
    }
    if (path === '/api/follow-ups/' && method === 'POST') {
      const data = route.request().postDataJSON(); state.posts.push(data)
      const row = { ...data, id: 100, customer_name: customers.find(item => item.id === Number(data.customer))?.name, contact_name: contacts.find(item => item.id === Number(data.contact))?.name, type_display: data.type === 'phone' ? '电话' : '邮件', attachments: [] }
      state.followUps.unshift(row)
      return route.fulfill({ json: row })
    }
    const attachmentMatch = path.match(/^\/api\/follow-ups\/(\d+)\/attachments\/(\d+)\/$/)
    if (attachmentMatch && method === 'DELETE') {
      const row = state.followUps.find(item => item.id === Number(attachmentMatch[1]))
      const attachmentId = Number(attachmentMatch[2])
      state.attachmentDeletes.push(path)
      if (row) row.attachments = row.attachments.filter(item => item.id !== attachmentId)
      return route.fulfill({ status: 204 })
    }
    const attachmentUploadMatch = path.match(/^\/api\/follow-ups\/(\d+)\/attachments\/$/)
    if (attachmentUploadMatch && method === 'POST') {
      const row = state.followUps.find(item => item.id === Number(attachmentUploadMatch[1]))
      state.uploads.push(path)
      const saved = { id: 500, name: '浏览器上传验收.txt', size: 24, content_type: 'text/plain', url: '/media/uat.txt' }
      if (row) row.attachments.push(saved)
      return route.fulfill({ json: [saved] })
    }
    if (contactMatch && method === 'PUT') {
      const row = state.contacts.find(item => item.id === Number(contactMatch[1]))
      const data = route.request().postDataJSON(); state.puts.push(data); Object.assign(row, data)
      row.customer_name = customers.find(item => item.id === Number(row.customer))?.name
      return route.fulfill({ json: row })
    }
    if (followUpMatch && method === 'PUT') {
      const row = state.followUps.find(item => item.id === Number(followUpMatch[1]))
      const data = route.request().postDataJSON(); state.puts.push(data); Object.assign(row, data)
      return route.fulfill({ json: row })
    }
    if ((contactMatch || followUpMatch) && method === 'DELETE') {
      state.deletes.push(path)
      return route.fulfill({ status: 204 })
    }
    if (path.startsWith('/api/contacts/') || path.startsWith('/api/follow-ups/')) {
      const row = contactMatch ? state.contacts.find(item => item.id === Number(contactMatch[1])) : state.followUps.find(item => item.id === Number(followUpMatch?.[1]))
      return route.fulfill({ json: row || {} })
    }
    return route.fulfill({ json: [] })
  })
  return state
}

async function assertVisibleBounds(page, selectors) {
  const result = await page.evaluate(selectors => ({
    viewport: innerWidth,
    pageWidth: document.documentElement.scrollWidth,
    items: selectors.flatMap(selector => [...document.querySelectorAll(selector)].map(element => {
      const box = element.getBoundingClientRect()
      return { selector, x: box.x, right: box.right, width: box.width, height: box.height }
    })),
  }), selectors)
  expect(result.pageWidth).toBeLessThanOrEqual(result.viewport)
  for (const item of result.items) {
    expect(item.x, JSON.stringify(item)).toBeGreaterThanOrEqual(0)
    expect(item.right, JSON.stringify(item)).toBeLessThanOrEqual(result.viewport + 1)
    expect(item.width, JSON.stringify(item)).toBeGreaterThan(0)
    expect(item.height, JSON.stringify(item)).toBeGreaterThan(0)
  }
}

for (const width of [1440, 1280, 1024]) {
  test(`contacts filters, grouped columns, and form fit ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 950 })
    const state = await mockApi(page)
    await page.goto('/contacts?customer=1&page=2')
    await expect(page.getByRole('textbox', { name: '搜索联系人' })).toHaveValue('')
    await expect(page.getByLabel('按客户筛选')).toHaveValue('1')
    await expect(page.getByLabel('按联系人类型筛选')).toHaveValue('')
    await expect(page.getByRole('navigation', { name: '联系人列表分页' })).toContainText('第 2 / 2 页')
    await assertVisibleBounds(page, ['.crm-filter-bar input', '.crm-filter-bar select', '.crm-filter-bar button', '.table-wrap', '.contact-list-table td:last-child .table-actions button'])
    expect(await page.locator('.crm-filter-bar').evaluate(element => getComputedStyle(element).gridTemplateColumns.split(' ').length)).toBe(4)
    for (const height of await page.locator('.crm-filter-bar input,.crm-filter-bar select,.crm-filter-bar button').evaluateAll(elements => elements.map(element => element.getBoundingClientRect().height))) expect(height).toBeGreaterThanOrEqual(40)
    await page.getByRole('button', { name: '新建联系人' }).click()
    await expect(page.getByRole('dialog', { name: '新建联系人' })).toBeVisible()
    await assertVisibleBounds(page, ['.crm-editor', '.crm-editor .form-grid select', '.crm-editor .modal-foot .btn'])
    await expect(page.getByRole('heading', { name: '所属客户与联系人资料' })).toBeVisible()
    await expect(state.posts).toHaveLength(0)
  })
}

test('contact create, duplicate advisory, primary edit and return query stay consistent', async ({ page }) => {
  const state = await mockApi(page)
  await page.goto('/contacts?search=Lin%20Yu%201&primary=primary')
  await expect(page.locator('.contact-list-table tbody tr')).toHaveCount(1)
  await expect(page.locator('.contact-list-table').first()).toContainText('WhatsApp')
  await page.getByRole('button', { name: '新建联系人' }).click()
  const dialog = page.getByRole('dialog', { name: '新建联系人' })
  await dialog.getByLabel('所属客户').selectOption('1')
  await dialog.getByLabel('姓名').fill('Lin Yu 1')
  await expect(dialog.getByText(/该客户已有相同姓名或联系方式/)).toBeVisible()
  await dialog.getByLabel('姓名').fill('新联系人 验收')
  await dialog.getByLabel('职位').fill('采购与海外项目负责人')
  await dialog.getByLabel('电话').fill('+86 13800000000')
  await dialog.getByLabel('WhatsApp').fill('+86 13900000000')
  await dialog.getByRole('button', { name: '保存联系人' }).click()
  await expect(page.getByRole('status').filter({ hasText: '联系人已创建' })).toBeVisible()
  expect(state.posts).toHaveLength(1)
  expect(state.posts[0].is_primary).toBe(false)
  await page.goto('/contacts?search=Lin%20Yu%201&primary=primary')
  await page.locator('.contact-list-table tbody tr').first().click()
  await expect.poll(() => new URL(page.url()).searchParams.get('detail')).toBe('1')
  await expect(page.getByRole('dialog', { name: '联系人详情' })).toBeVisible()
  await expect(new URL(page.url()).searchParams.get('search')).toBe('Lin Yu 1')
})

for (const width of [1440, 1280, 1024]) {
  test(`follow-up filters, detailed groups, and long content fit ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 950 })
    await mockApi(page)
    await page.goto('/follow-ups?customer=1&type=email&from=2026-10-03&to=2026-10-14&sort=oldest&page=2')
    await expect(page.getByLabel('按客户筛选')).toHaveValue('1')
    await expect(page.getByLabel('按跟进方式筛选')).toHaveValue('email')
    await expect(page.getByLabel('跟进开始日期')).toHaveValue('2026-10-03')
    await expect(page.getByLabel('跟进结束日期')).toHaveValue('2026-10-14')
    await expect(page.getByLabel('跟进排序')).toHaveValue('oldest')
    await expect(page.locator('.follow-up-list-table tbody tr')).toHaveCount(10)
    await assertVisibleBounds(page, ['.crm-filter-bar input', '.crm-filter-bar select', '.crm-filter-bar button', '.table-wrap', '.follow-up-list-table td:last-child .table-actions button'])
    expect(await page.locator('.crm-filter-bar').evaluate(element => getComputedStyle(element).gridTemplateColumns.split(' ').length)).toBe(width > 1100 ? 6 : 4)
    await page.locator('.follow-up-list-table tbody tr').first().click()
    await expect(page.getByRole('dialog', { name: '跟进详情' })).toBeVisible()
    await expect(page.locator('.follow-up-attachments-card')).toContainText('1 个附件')
    await expect(page.locator('.follow-up-detail-content')).toBeVisible()
    await page.getByRole('button', { name: /返回列表/ }).click()
    await expect(page.getByRole('textbox', { name: '搜索跟进记录' })).toBeVisible()
    await expect(new URL(page.url()).searchParams.get('customer')).toBe('1')
    await page.getByRole('button', { name: '新建跟进记录' }).click()
    const dialog = page.getByRole('dialog', { name: '新建跟进记录' })
    await expect(dialog.getByRole('heading', { name: '客户与沟通方式' })).toBeVisible()
    await assertVisibleBounds(page, ['.crm-editor', '.crm-editor .form-grid select', '.crm-editor .modal-foot .btn'])
    await expect(dialog.getByText(/跟进记录或客户回复至少填写一项/)).toBeVisible()
  })
}

test('follow-up search and due filters remain in URL and saved text updates list', async ({ page }) => {
  const state = await mockApi(page)
  await page.goto('/follow-ups?search=产品资料沟通&due=true')
  await expect(page.locator('.follow-up-list-table tbody tr')).toHaveCount(20)
  await expect(page.getByLabel('当前跟进筛选')).toContainText('今日及逾期待跟进')
  await page.getByLabel('搜索跟进记录').fill('客户回复')
  await expect.poll(() => new URL(page.url()).searchParams.get('search')).toBe('客户回复')
  await page.getByRole('button', { name: '显示全部记录' }).click()
  await expect.poll(() => new URL(page.url()).searchParams.get('due')).toBeNull()
  await page.getByRole('button', { name: '新建跟进记录' }).click()
  const dialog = page.getByRole('dialog', { name: '新建跟进记录' })
  await dialog.getByLabel('客户', { exact: true }).selectOption('1')
  await dialog.getByLabel('跟进方式').fill('电话')
  await dialog.getByLabel('跟进方式').press('Enter')
  await dialog.getByLabel('沟通记录').fill('本轮真实操作路径记录')
  const upload = dialog.locator('input[type="file"]')
  await upload.setInputFiles({ name: '待上传后移除.txt', mimeType: 'text/plain', buffer: Buffer.from('remove local upload') })
  await expect(dialog.getByText('待上传后移除.txt')).toBeVisible()
  await dialog.getByRole('button', { name: '移除待上传附件' }).click()
  await upload.setInputFiles({ name: '浏览器上传验收.txt', mimeType: 'text/plain', buffer: Buffer.from('isolated upload') })
  await expect(dialog.getByText('浏览器上传验收.txt')).toBeVisible()
  await dialog.getByRole('button', { name: '保存跟进' }).click()
  await expect(page.getByRole('status').filter({ hasText: '跟进记录已保存' })).toBeVisible()
  expect(state.posts.at(-1)).toMatchObject({ customer: 1, content: '本轮真实操作路径记录', next_follow_up_mode: 'keep', next_follow_up: null })
  expect(state.uploads).toHaveLength(1)
})

test('saved attachment delete can be cancelled, confirmed, and remains removed after reopening', async ({ page }) => {
  const state = await mockApi(page)
  await page.goto('/follow-ups')
  const row = page.locator('.follow-up-list-table tbody tr').filter({ has: page.getByText('产品资料沟通 1', { exact: true }) })
  await row.getByRole('button', { name: '编辑跟进记录' }).click()
  let editor = page.getByRole('dialog', { name: '编辑跟进记录' })
  const removeButton = editor.getByRole('button', { name: '删除已保存附件 验收附件-1.txt' })
  await removeButton.click()
  const confirmation = page.getByRole('dialog', { name: '删除附件' })
  await confirmation.getByRole('button', { name: '取消' }).click()
  await expect(editor.getByText('验收附件-1.txt')).toBeVisible()
  expect(state.attachmentDeletes).toHaveLength(0)
  await editor.getByRole('button', { name: '取消' }).click()
  await row.getByRole('button', { name: '编辑跟进记录' }).click()
  editor = page.getByRole('dialog', { name: '编辑跟进记录' })
  await editor.getByRole('button', { name: '删除已保存附件 验收附件-1.txt' }).click()
  await page.getByRole('dialog', { name: '删除附件' }).getByRole('button', { name: '确认删除' }).click()
  await expect(editor.getByText('验收附件-1.txt')).toHaveCount(0)
  expect(state.attachmentDeletes).toEqual(['/api/follow-ups/1/attachments/1/'])
  await editor.getByRole('button', { name: '取消' }).click()
  await row.getByRole('button', { name: '编辑跟进记录' }).click()
  editor = page.getByRole('dialog', { name: '编辑跟进记录' })
  await expect(editor.getByText('验收附件-1.txt')).toHaveCount(0)
})
