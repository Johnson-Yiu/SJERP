export function followUpError(form) {
  if (!String(form.content || '').trim() && !String(form.result || '').trim()) {
    return '请至少填写跟进记录或客户回复，避免保存空白跟进。'
  }
  if (form.next_follow_up_mode === 'set' && !form.next_follow_up) return '请填写新的跟进日期。'
  return ''
}
