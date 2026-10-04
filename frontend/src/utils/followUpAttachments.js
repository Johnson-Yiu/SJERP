export function removeSavedFollowUpAttachmentFromRows(rows, followUpId, attachmentId) {
  return rows.map(row => String(row.id) === String(followUpId)
    ? {
        ...row,
        attachments: (row.attachments || []).filter(item => String(item.id) !== String(attachmentId)),
      }
    : row)
}

export async function confirmAndDeleteSavedFollowUpAttachment({
  followUpId,
  attachment,
  api,
  confirmDialog,
  onDeleted,
  onError,
}) {
  if (!followUpId || !attachment?.id) return false

  const confirmed = await confirmDialog({
    title: '删除附件',
    message: `确定删除“${attachment.name}”吗？附件删除将立即生效，取消或关闭本次 FollowUp 编辑都无法恢复。`,
    confirmText: '确认删除',
    cancelText: '取消',
    danger: true,
  })
  if (!confirmed) return false

  try {
    await api.delete(`/follow-ups/${followUpId}/attachments/${attachment.id}/`)
  } catch (error) {
    onError?.(error)
    return false
  }

  await onDeleted?.(attachment)
  return true
}
